"""Club General-Manager agent — AI opponent when user plays as player."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from negotiation.prompts import CLUB_AGENT_PROMPT
from negotiation.term_sheet import TermSheet, TermSheetAction, ActionType
from orchestrator.config import settings

if TYPE_CHECKING:
    from negotiation.state import NegotiationState

logger = logging.getLogger(__name__)


def _build_user_message(state: "NegotiationState") -> str:
    """Assemble the context payload the LLM sees each turn."""
    profile = state.player_profile
    constraints = state.club_constraints
    market = state.market_context or {}

    parts = [
        "=== PLAYER PROFILE ===",
        json.dumps(profile, indent=2),
        "",
        "=== CLUB CONSTRAINTS ===",
        json.dumps(constraints, indent=2),
        "",
        "=== MARKET CONTEXT ===",
        json.dumps(market, indent=2),
        "",
    ]

    if state.rounds:
        parts.append("=== NEGOTIATION HISTORY ===")
        for r in state.rounds:
            parts.append(
                f"Round {r['round_number']} ({r['side']}): {r['action']} — "
                f"{json.dumps(r.get('term_sheet', {}))}"
            )
            if r.get("reasoning"):
                parts.append(f"  Reasoning: {r['reasoning']}")
        parts.append("")

        # Reference the user's last counter specifically
        user_rounds = [r for r in state.rounds if r["side"] == "player"]
        if user_rounds:
            last_user = user_rounds[-1]
            last_user_term = last_user.get("term_sheet", {})
            parts.append("=== USER'S LATEST COUNTER (PLAYER SIDE) ===")
            parts.append(json.dumps(last_user_term, indent=2))
            parts.append(f"Their reasoning: {last_user.get('reasoning', 'N/A')}")
            parts.append("")
            parts.append(
                "IMPORTANT: You must reference the user's specific demands above. "
                "Move toward their position incrementally while protecting club interests. "
                "If they have countered multiple times, show meaningful movement."
            )
            parts.append("")

    if not state.rounds:
        parts.append("This is the FIRST round. You must PROPOSE an initial term sheet.")
    else:
        parts.append(
            f"This is round {state.current_round + 1} of {state.max_rounds}. "
            "Evaluate the player's last counter and respond."
        )

    return "\n".join(parts)


async def run_club_agent(state: "NegotiationState") -> TermSheetAction:
    """Call the LLM and return a structured TermSheetAction."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.4,
        timeout=settings.AGENT_TIMEOUT,
    )

    messages = [
        SystemMessage(content=CLUB_AGENT_PROMPT),
        HumanMessage(content=_build_user_message(state)),
    ]

    try:
        structured_llm = llm.with_structured_output(TermSheetAction)
        result: TermSheetAction = await structured_llm.ainvoke(messages)
        logger.info("Club agent returned action=%s", result.action)
        return result
    except Exception as e:
        logger.error("Club agent LLM call failed: %s", e)
        return _fallback_offer(state)


def _fallback_offer(state: "NegotiationState") -> TermSheetAction:
    """Deterministic fallback if the LLM fails — smarter, references user offers."""
    market = state.market_context or {}
    salary_range = market.get("salary_range", {})
    low = salary_range.get("low_eur", 5_000_000)
    mid = salary_range.get("mid_eur", 8_000_000)
    budget = state.club_constraints.get("budget_eur", low)
    max_years = state.club_constraints.get("max_years", 3)

    # If we have user counter-offers, move toward them
    user_rounds = [r for r in state.rounds if r["side"] == "player"]
    if user_rounds:
        last_user_base = user_rounds[-1].get("term_sheet", {}).get("base_salary_eur", 0)
        club_rounds = [r for r in state.rounds if r["side"] == "club"]
        last_club_base = club_rounds[-1].get("term_sheet", {}).get("base_salary_eur", low) if club_rounds else low

        # Move 30% toward the user's demand each round
        base = int(last_club_base + (last_user_base - last_club_base) * 0.3)
        base = min(base, budget)  # Never exceed budget

        # If above median after many rounds, consider accepting
        if base >= mid and state.current_round >= 4:
            return TermSheetAction(
                action=ActionType.ACCEPT,
                term_sheet=None,
                reasoning=f"After {state.current_round} rounds, player demands at EUR {last_user_base:,} "
                          f"are within acceptable range. Accepting.",
            )
    else:
        base = min(low, budget)

    sheet = TermSheet(
        player_name=state.player_profile.get("name", "Unknown"),
        position=state.player_profile.get("position", "CM"),
        base_salary_eur=base,
        signing_bonus_eur=int(base * 0.10),
        performance_bonus_eur=int(base * 0.05),
        contract_years=min(max_years, 3),
    )

    action = ActionType.PROPOSE if not state.rounds else ActionType.COUNTER
    return TermSheetAction(
        action=action,
        term_sheet=sheet,
        reasoning=f"{'Opening' if action == ActionType.PROPOSE else 'Counter'} offer at EUR {base:,}/yr "
                  f"— {'initial conservative position' if not user_rounds else 'moving toward player demands'}.",
    )
