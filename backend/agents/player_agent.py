"""Player agent — AI opponent when user plays as club."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from negotiation.prompts import PLAYER_AGENT_PROMPT
from negotiation.term_sheet import TermSheet, TermSheetAction, ActionType
from orchestrator.config import settings

if TYPE_CHECKING:
    from negotiation.state import NegotiationState

logger = logging.getLogger(__name__)


def _build_user_message(state: "NegotiationState") -> str:
    profile = state.player_profile
    market = state.market_context or {}
    priorities = state.player_priorities

    parts = [
        "=== PLAYER PROFILE ===",
        json.dumps(profile, indent=2),
        "",
        "=== PLAYER PRIORITIES ===",
        json.dumps(priorities, indent=2),
        "",
        "=== MARKET CONTEXT ===",
        json.dumps(market, indent=2),
        "",
        "=== NEGOTIATION HISTORY ===",
    ]

    for r in state.rounds:
        parts.append(
            f"Round {r['round_number']} ({r['side']}): {r['action']} — "
            f"{json.dumps(r.get('term_sheet', {}))}"
        )
        if r.get("reasoning"):
            parts.append(f"  Reasoning: {r['reasoning']}")
        if r.get("constraint_violations"):
            parts.append(f"  Violations: {r['constraint_violations']}")

    parts.append("")

    # Reference the user's last offer specifically
    user_rounds = [r for r in state.rounds if r["side"] == "club"]
    if user_rounds:
        last_user = user_rounds[-1]
        last_user_term = last_user.get("term_sheet", {})
        parts.append("=== USER'S LATEST OFFER (CLUB SIDE) ===")
        parts.append(json.dumps(last_user_term, indent=2))
        parts.append(f"Their reasoning: {last_user.get('reasoning', 'N/A')}")
        parts.append("")
        parts.append(
            "IMPORTANT: You must reference the user's specific offer above. "
            "Show you understand what they offered and explain why you need more "
            "or why you are willing to accept. Be specific about which terms need adjustment."
        )
        parts.append("")

    parts.append(
        f"This is round {state.current_round + 1} of {state.max_rounds}. "
        "Evaluate the club's latest offer and respond."
    )

    return "\n".join(parts)


async def run_player_agent(state: "NegotiationState") -> TermSheetAction:
    """Call the LLM and return a structured TermSheetAction."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.5,
        timeout=settings.AGENT_TIMEOUT,
    )

    messages = [
        SystemMessage(content=PLAYER_AGENT_PROMPT),
        HumanMessage(content=_build_user_message(state)),
    ]

    try:
        structured_llm = llm.with_structured_output(TermSheetAction)
        result: TermSheetAction = await structured_llm.ainvoke(messages)
        logger.info("Player agent returned action=%s", result.action)
        return result
    except Exception as e:
        logger.error("Player agent LLM call failed: %s", e)
        return _fallback_response(state)


def _fallback_response(state: "NegotiationState") -> TermSheetAction:
    """Deterministic fallback — smarter, references user's club offers."""
    market = state.market_context or {}
    salary_range = market.get("salary_range", {})
    high = salary_range.get("high_eur", 15_000_000)
    mid = salary_range.get("mid_eur", 10_000_000)
    low = salary_range.get("low_eur", mid * 0.7)

    # Get user's (club) offers
    user_rounds = [r for r in state.rounds if r["side"] == "club"]
    player_rounds = [r for r in state.rounds if r["side"] == "player"]

    if user_rounds:
        last_user_base = user_rounds[-1].get("term_sheet", {}).get("base_salary_eur", 0)

        # If user's offer meets median, accept
        if last_user_base >= mid:
            return TermSheetAction(
                action=ActionType.ACCEPT,
                term_sheet=None,
                reasoning=f"Club offer of EUR {last_user_base:,}/yr meets market median "
                          f"(EUR {mid:,}). Accepting.",
            )

        # If very low after 3+ rounds, walk away
        if last_user_base < low * 0.85 and state.current_round >= 3:
            return TermSheetAction(
                action=ActionType.WALK_AWAY,
                term_sheet=None,
                reasoning=f"Club offers remain at EUR {last_user_base:,}/yr, far below market "
                          f"floor (EUR {int(low):,}) after {state.current_round} rounds.",
            )

        # Counter — move 25% toward user's offer from our last position
        last_player_base = high
        if player_rounds:
            last_player_base = player_rounds[-1].get("term_sheet", {}).get("base_salary_eur", high)

        counter_base = int(last_player_base - (last_player_base - last_user_base) * 0.25)
        counter_base = max(counter_base, int(mid * 0.9))  # Don't go below ~90% of median
    else:
        # First response — open at high end
        counter_base = high

    sheet = TermSheet(
        player_name=state.player_profile.get("name", "Unknown"),
        position=state.player_profile.get("position", "CM"),
        base_salary_eur=counter_base,
        signing_bonus_eur=int(counter_base * 0.15),
        performance_bonus_eur=int(counter_base * 0.10),
        contract_years=3,
        image_rights_pct=20,
    )

    return TermSheetAction(
        action=ActionType.COUNTER,
        term_sheet=sheet,
        reasoning=f"Counter at EUR {counter_base:,}/yr — "
                  f"{'opening position at market high' if not user_rounds else 'moving toward club offer while protecting player value'}.",
    )
