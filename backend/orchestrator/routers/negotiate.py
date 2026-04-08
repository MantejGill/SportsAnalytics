"""Negotiate router — HITL negotiation with two-graph pause/resume pattern."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from negotiation.graph import GraphState, opening_graph, round_graph
from negotiation.metrics import compute_negotiation_metrics
from negotiation.state import NegotiationState
from orchestrator.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["negotiate"])

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_negotiations: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class NegotiateRequest(BaseModel):
    player_name: str
    club_name: str
    budget_eur: int
    max_years: int = 4
    priorities: list[str] = []
    user_side: str = "player"
    walk_away_threshold_eur: int = 0
    player_priorities: list[str] = []


class NegotiateResponse(BaseModel):
    request_id: str
    stream_url: str
    status: str


class DecideRequest(BaseModel):
    action: str = Field(..., description="ACCEPT, COUNTER, or WALK_AWAY")
    term_sheet: dict | None = None
    reasoning: str = ""


class DecideResponse(BaseModel):
    request_id: str
    action: str
    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _run_graph(graph, initial_state: GraphState, entry: dict) -> GraphState:
    """Run a compiled graph via astream, pushing events to the SSE queue."""
    queue: asyncio.Queue = entry["queue"]
    prev_event_count = len(entry["events"])
    final_state = initial_state

    async for chunk in graph.astream(initial_state, stream_mode="values"):
        final_state = chunk
        events = chunk.get("events", [])
        # Push only NEW events
        if len(events) > prev_event_count:
            for evt in events[prev_event_count:]:
                entry["events"].append(evt)
                await queue.put(evt)
            prev_event_count = len(events)
        entry["state"] = chunk.get("negotiation", entry["state"])

    return final_state


# ---------------------------------------------------------------------------
# Background runner for opening
# ---------------------------------------------------------------------------

async def _run_opening(request_id: str, initial_state: GraphState) -> None:
    entry = _negotiations[request_id]
    queue: asyncio.Queue = entry["queue"]

    try:
        final_state = await _run_graph(opening_graph, initial_state, entry)
        ns = NegotiationState.from_dict(entry["state"])

        if ns.status in ("WALKED_AWAY", "ACCEPTED"):
            entry["status"] = "completed"
            await queue.put({
                "type": "negotiation_complete",
                "data": {
                    "status": ns.status,
                    "total_rounds": ns.current_round,
                    "final_term_sheet": ns.rounds[-1].get("term_sheet") if ns.rounds else None,
                    "rounds": ns.rounds,
                },
            })
            await queue.put(None)
        else:
            # War room done, awaiting user decision
            entry["status"] = "awaiting_user"
            logger.info("Opening graph done for %s — awaiting user decision", request_id)
            # DON'T close the SSE stream — keep it alive for the decision phase

    except Exception as e:
        logger.exception("Opening graph failed for %s", request_id)
        entry["status"] = "error"
        entry["error"] = str(e)
        error_evt = {"type": "error", "data": {"message": str(e)}}
        entry["events"].append(error_evt)
        await queue.put(error_evt)
        await queue.put(None)


# ---------------------------------------------------------------------------
# Background runner for a round (after user decides)
# ---------------------------------------------------------------------------

async def _run_round(request_id: str, user_decision: dict) -> None:
    entry = _negotiations[request_id]
    queue: asyncio.Queue = entry["queue"]

    try:
        # Build state with user decision injected
        ns = NegotiationState.from_dict(entry["state"])
        ns.user_decision = user_decision
        ns.pending_user_action = False
        ns.status = "NEGOTIATING"

        round_state: GraphState = {
            "negotiation": ns.to_dict(),
            "events": list(entry["events"]),  # carry forward
            "request_id": request_id,
        }

        final_state = await _run_graph(round_graph, round_state, entry)
        ns = NegotiationState.from_dict(entry["state"])

        if ns.status in ("WALKED_AWAY", "ACCEPTED", "MAX_ROUNDS"):
            entry["status"] = "completed"
            summary = {
                "type": "negotiation_complete",
                "data": {
                    "status": ns.status,
                    "total_rounds": ns.current_round,
                    "final_term_sheet": ns.rounds[-1].get("term_sheet") if ns.rounds else None,
                    "rounds": ns.rounds,
                },
            }
            entry["events"].append(summary)
            await queue.put(summary)
            await queue.put(None)
        else:
            # Another war room pause — awaiting user again
            entry["status"] = "awaiting_user"
            logger.info("Round graph done for %s — awaiting next user decision", request_id)

    except Exception as e:
        logger.exception("Round graph failed for %s", request_id)
        entry["status"] = "error"
        entry["error"] = str(e)
        error_evt = {"type": "error", "data": {"message": str(e)}}
        entry["events"].append(error_evt)
        await queue.put(error_evt)
        await queue.put(None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/negotiate", response_model=NegotiateResponse)
async def start_negotiation(req: NegotiateRequest) -> NegotiateResponse:
    request_id = str(uuid.uuid4())

    if req.user_side not in ("club", "player"):
        raise HTTPException(status_code=400, detail="user_side must be 'club' or 'player'")

    all_priorities = req.player_priorities or req.priorities or ["high_salary", "short_contract"]

    ns = NegotiationState(
        player_profile={"name": req.player_name, "age": 25, "position": "CM",
                        "current_club": "", "stats": {}},
        club_constraints={"club_name": req.club_name, "budget_eur": req.budget_eur,
                          "max_years": req.max_years, "priorities": req.priorities},
        player_priorities=all_priorities,
        user_side=req.user_side,
        walk_away_threshold_eur=req.walk_away_threshold_eur,
        max_rounds=settings.MAX_NEGOTIATION_ROUNDS,
    )

    # Enrich player profile from sample data
    from agents.market_predictor import _load_players
    players = _load_players()
    player_key = req.player_name.lower()
    if player_key in players:
        pd = players[player_key]
        ns.player_profile = {"name": pd["name"], "age": pd["age"],
                             "position": pd["position"],
                             "current_club": pd["current_club"],
                             "stats": pd.get("stats", {})}

    initial_state: GraphState = {
        "negotiation": ns.to_dict(),
        "events": [],
        "request_id": request_id,
    }

    queue: asyncio.Queue = asyncio.Queue()
    _negotiations[request_id] = {
        "state": ns.to_dict(),
        "events": [],
        "status": "running",
        "queue": queue,
        "error": None,
    }

    asyncio.create_task(_run_opening(request_id, initial_state))

    return NegotiateResponse(
        request_id=request_id,
        stream_url=f"/api/stream/{request_id}",
        status="running",
    )


@router.get("/stream/{request_id}")
async def stream_events(request_id: str) -> EventSourceResponse:
    if request_id not in _negotiations:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    entry = _negotiations[request_id]

    async def event_generator():
        queue: asyncio.Queue = entry["queue"]

        # Replay past events
        for evt in list(entry["events"]):
            yield {"event": evt.get("type", "message"),
                   "data": json.dumps(evt.get("data", evt))}

        # If done or awaiting user, send status and keep alive
        if entry["status"] == "awaiting_user":
            yield {"event": "status", "data": json.dumps({"status": "awaiting_user"})}

        if entry["status"] in ("completed", "error"):
            return

        # Stream live events
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60)
            except asyncio.TimeoutError:
                # Send keepalive
                yield {"event": "keepalive", "data": json.dumps({"status": entry["status"]})}
                continue

            if event is None:
                break
            yield {"event": event.get("type", "message"),
                   "data": json.dumps(event.get("data", event))}

    return EventSourceResponse(event_generator())


@router.post("/decide/{request_id}", response_model=DecideResponse)
async def submit_decision(request_id: str, req: DecideRequest) -> DecideResponse:
    if request_id not in _negotiations:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    entry = _negotiations[request_id]
    if entry["status"] != "awaiting_user":
        raise HTTPException(status_code=400,
                            detail=f"Not awaiting decision (status={entry['status']})")

    if req.action not in ("ACCEPT", "COUNTER", "WALK_AWAY"):
        raise HTTPException(status_code=400, detail="action must be ACCEPT, COUNTER, or WALK_AWAY")

    if req.action == "COUNTER" and not req.term_sheet:
        raise HTTPException(status_code=400, detail="term_sheet required for COUNTER")

    entry["status"] = "running"

    user_decision = {
        "action": req.action,
        "term_sheet": req.term_sheet,
        "reasoning": req.reasoning,
    }

    # Run the next round graph in background
    asyncio.create_task(_run_round(request_id, user_decision))

    return DecideResponse(
        request_id=request_id,
        action=req.action,
        status="running",
    )


@router.get("/metrics/{request_id}")
async def get_metrics(request_id: str) -> dict:
    """Return validation metrics for a negotiation session."""
    if request_id not in _negotiations:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    entry = _negotiations[request_id]
    ns = NegotiationState.from_dict(entry["state"])
    metrics = compute_negotiation_metrics(ns)
    return {"request_id": request_id, "metrics": metrics}


@router.get("/negotiation/{request_id}")
async def get_negotiation(request_id: str) -> dict:
    if request_id not in _negotiations:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    entry = _negotiations[request_id]
    return {
        "request_id": request_id,
        "status": entry["status"],
        "state": entry["state"],
        "events": entry["events"],
        "error": entry["error"],
    }
