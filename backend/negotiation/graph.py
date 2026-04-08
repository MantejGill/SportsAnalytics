"""LangGraph negotiation workflows — split into two graphs for HITL pause/resume."""

from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END

from agents.club_agent import run_club_agent
from agents.adapters import get_checker, get_predictor
from agents.player_agent import run_player_agent
from agents.strategy_advisor import compute_strategy
from agents.war_room import run_war_room
from negotiation.state import NegotiationState
from negotiation.term_sheet import ActionType
from orchestrator.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class GraphState(TypedDict, total=False):
    negotiation: dict          # serialised NegotiationState
    events: list[dict]         # accumulated SSE events
    request_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unpack(state: GraphState) -> NegotiationState:
    return NegotiationState.from_dict(state["negotiation"])

def _pack(state: GraphState, ns: NegotiationState) -> GraphState:
    return {**state, "negotiation": ns.to_dict()}

def _emit(state: GraphState, event: dict) -> GraphState:
    events = list(state.get("events", []))
    events.append(event)
    return {**state, "events": events}


# ---------------------------------------------------------------------------
# GRAPH 1: "opening" — runs from start until war room completes, then ENDS.
# Flow: market_predictor → ai_club_proposes → constraint_check → war_room → END
# ---------------------------------------------------------------------------

async def market_predictor_node(state: GraphState) -> GraphState:
    ns = _unpack(state)
    ns.active_agent = "market_predictor"
    ns.append_log("Running market prediction...")

    market_ctx = get_predictor().predict(ns.player_profile)
    ns.market_context = market_ctx

    strategy = compute_strategy(market_ctx, ns.club_constraints)
    ns.append_log(f"Strategy computed: ZOPA salary {strategy['zone_of_possible_agreement']}")
    ns.status = "NEGOTIATING"

    state = _pack(state, ns)
    state = _emit(state, {
        "type": "market_prediction",
        "data": {"market_context": market_ctx, "strategy": strategy},
    })
    return state


async def ai_club_proposes_node(state: GraphState) -> GraphState:
    ns = _unpack(state)
    ns.active_agent = "club_agent"
    ns.append_log(f"AI Club proposing (round {ns.current_round + 1})...")

    result = await run_club_agent(ns)
    term_dict = result.term_sheet.model_dump() if result.term_sheet else None

    ns.append_round(
        side="club",
        action=result.action.value,
        term_sheet=term_dict,
        reasoning=result.reasoning,
    )

    if result.action == ActionType.WALK_AWAY:
        ns.status = "WALKED_AWAY"
        ns.append_log("AI Club walked away.")

    state = _pack(state, ns)
    state = _emit(state, {
        "type": "opponent_offer",
        "data": {
            "side": "club",
            "round": ns.current_round,
            "action": result.action.value,
            "term_sheet": term_dict,
            "reasoning": result.reasoning,
        },
    })
    return state


async def constraint_check_node(state: GraphState) -> GraphState:
    ns = _unpack(state)
    ns.active_agent = "constraint_checker"

    if not ns.rounds:
        return _pack(state, ns)

    last_round = ns.rounds[-1]
    term_sheet = last_round.get("term_sheet", {})

    result = get_checker().check(
        term_sheet=term_sheet,
        market_context=ns.market_context,
        rounds=ns.rounds,
        current_round=ns.current_round,
        club_constraints=ns.club_constraints,
    )

    last_round["constraint_violations"] = result.get("violations", [])
    ns.append_log(f"Constraint check: valid={result['valid']}")

    state = _pack(state, ns)
    state = _emit(state, {"type": "constraint_check", "data": result})
    return state


async def war_room_node(state: GraphState) -> GraphState:
    ns = _unpack(state)

    if ns.status in ("WALKED_AWAY", "ACCEPTED"):
        return _pack(state, ns)

    ns.active_agent = "war_room"
    ns.append_log("Running War Room analysis...")

    war_room_results = await run_war_room(ns)
    ns.war_room_results = war_room_results
    ns.pending_user_action = True
    ns.status = "AWAITING_USER_DECISION"

    state = _pack(state, ns)
    state = _emit(state, {"type": "war_room_complete", "data": war_room_results})
    return state


def _skip_if_done(state: GraphState) -> str:
    ns = _unpack(state)
    if ns.status in ("WALKED_AWAY", "ACCEPTED"):
        return "end"
    return "continue"


def build_opening_graph():
    """Graph 1: market → opponent proposes → constraint check → war room → END."""
    g = StateGraph(GraphState)
    g.add_node("market_predictor", market_predictor_node)
    g.add_node("ai_club_proposes", ai_club_proposes_node)
    g.add_node("constraint_check", constraint_check_node)
    g.add_node("war_room", war_room_node)

    g.set_entry_point("market_predictor")
    g.add_edge("market_predictor", "ai_club_proposes")
    g.add_conditional_edges("ai_club_proposes", _skip_if_done, {"continue": "constraint_check", "end": END})
    g.add_edge("constraint_check", "war_room")
    g.add_edge("war_room", END)
    return g.compile()


# ---------------------------------------------------------------------------
# GRAPH 2: "round" — runs after user decides. Applies user decision,
# then AI opponent responds, constraint check, war room → END (pause again).
# Flow: apply_user_decision → ai_club_proposes → constraint_check → war_room → END
# ---------------------------------------------------------------------------

async def apply_user_decision_node(state: GraphState) -> GraphState:
    """Apply the user's ACCEPT/COUNTER/WALK_AWAY decision."""
    ns = _unpack(state)
    decision = ns.user_decision or {}
    action_str = decision.get("action", "COUNTER")
    user_term_sheet = decision.get("term_sheet")

    ns.active_agent = "user"
    ns.pending_user_action = False
    ns.status = "NEGOTIATING"

    if action_str == "ACCEPT":
        # User accepts the last club offer
        ns.append_round(side="player", action="ACCEPT", term_sheet=None,
                        reasoning="User accepted the offer.")
        ns.status = "ACCEPTED"
        ns.append_log("User accepted the offer.")
    elif action_str == "WALK_AWAY":
        ns.append_round(side="player", action="WALK_AWAY", term_sheet=None,
                        reasoning="User walked away from negotiations.")
        ns.status = "WALKED_AWAY"
        ns.append_log("User walked away.")
    else:  # COUNTER
        ns.append_round(side="player", action="COUNTER",
                        term_sheet=user_term_sheet,
                        reasoning=decision.get("reasoning", "User counter-offer."))
        ns.append_log(f"User countered: base={user_term_sheet.get('base_salary_eur') if user_term_sheet else '?'}")

        # Validate user's counter-offer with constraint checker
        if user_term_sheet:
            result = get_checker().check(
                term_sheet=user_term_sheet,
                market_context=ns.market_context,
                rounds=ns.rounds,
                current_round=ns.current_round,
                club_constraints=ns.club_constraints,
            )
            ns.rounds[-1]["constraint_violations"] = result.get("violations", [])
            if result.get("violations"):
                ns.append_log(f"User counter has constraint issues: {result['violations']}")

    # Clear war room for next round
    ns.war_room_results = None
    ns.user_decision = None

    state = _pack(state, ns)
    state = _emit(state, {
        "type": "user_decision",
        "data": {
            "side": "player",
            "action": action_str,
            "term_sheet": user_term_sheet,
        },
    })
    return state


def _after_user_decision(state: GraphState) -> str:
    ns = _unpack(state)
    if ns.status in ("ACCEPTED", "WALKED_AWAY"):
        return "end"
    if ns.current_round >= ns.max_rounds:
        ns.status = "MAX_ROUNDS"
        state["negotiation"] = ns.to_dict()
        return "end"
    return "continue"


def build_round_graph():
    """Graph 2: user decision → AI opponent → constraint → war room → END."""
    g = StateGraph(GraphState)
    g.add_node("apply_user_decision", apply_user_decision_node)
    g.add_node("ai_club_proposes", ai_club_proposes_node)
    g.add_node("constraint_check", constraint_check_node)
    g.add_node("war_room", war_room_node)

    g.set_entry_point("apply_user_decision")
    g.add_conditional_edges("apply_user_decision", _after_user_decision,
                            {"continue": "ai_club_proposes", "end": END})
    g.add_conditional_edges("ai_club_proposes", _skip_if_done,
                            {"continue": "constraint_check", "end": END})
    g.add_edge("constraint_check", "war_room")
    g.add_edge("war_room", END)
    return g.compile()


# Singletons
opening_graph = build_opening_graph()
round_graph = build_round_graph()
