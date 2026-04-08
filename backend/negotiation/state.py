"""Negotiation state representation."""

from __future__ import annotations

import typing
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class NegotiationState:
    """Full state of a single contract negotiation session."""

    # ---- Core parties ---------------------------------------------------
    player_profile: dict = field(default_factory=dict)
    # Expected keys: name, age, position, current_club, stats

    club_constraints: dict = field(default_factory=dict)
    # Expected keys: budget_eur, max_years, priorities

    player_priorities: list[str] = field(default_factory=list)
    # e.g. ["high_salary", "image_rights", "no_trade_clause"]

    # ---- HITL fields ----------------------------------------------------
    user_side: str = ""
    # "club" or "player" — which side the human is playing

    walk_away_threshold_eur: int = 0
    # User-specified walk-away threshold (annual salary)

    war_room_results: dict | None = None
    # Latest war room advisory analysis

    pending_user_action: bool = False
    # True when the graph is paused waiting for user decision

    user_decision: dict | None = None
    # Populated by POST /api/decide: {action, term_sheet?}

    # ---- Market intelligence -------------------------------------------
    market_context: dict | None = None
    # Keys: predicted_value_eur, p25_eur, median_eur, p75_eur, comparables

    # ---- Negotiation history -------------------------------------------
    rounds: list[dict] = field(default_factory=list)
    # Each round dict:
    #   round_number: int
    #   side: "club" | "player"
    #   action: "PROPOSE" | "COUNTER" | "ACCEPT" | "WALK_AWAY"
    #   term_sheet: dict (serialised TermSheet)
    #   reasoning: str
    #   constraint_violations: list[str]
    #   timestamp: str  (ISO-8601)

    current_round: int = 0
    max_rounds: int = 8

    # ---- Session metadata ----------------------------------------------
    status: str = "SETUP"
    # Allowed: SETUP, NEGOTIATING, AWAITING_USER_DECISION, ACCEPTED, WALKED_AWAY, MAX_ROUNDS

    active_agent: str = ""
    # Name of the agent currently executing

    logs: list[dict] = field(default_factory=list)
    # Free-form log entries: {timestamp, level, message, agent?}

    # ---- Helpers -------------------------------------------------------

    def append_log(self, message: str, level: str = "info", agent: str = "") -> None:
        self.logs.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "message": message,
                "agent": agent or self.active_agent,
            }
        )

    def append_round(
        self,
        side: str,
        action: str,
        term_sheet: dict | None,
        reasoning: str,
        violations: list[str] | None = None,
    ) -> None:
        self.current_round += 1
        self.rounds.append(
            {
                "round_number": self.current_round,
                "side": side,
                "action": action,
                "term_sheet": term_sheet or {},
                "reasoning": reasoning,
                "constraint_violations": violations or [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def to_dict(self) -> dict:
        """Serialise the entire state to a plain dict (JSON-safe)."""
        return {
            "player_profile": self.player_profile,
            "club_constraints": self.club_constraints,
            "player_priorities": self.player_priorities,
            "user_side": self.user_side,
            "walk_away_threshold_eur": self.walk_away_threshold_eur,
            "war_room_results": self.war_room_results,
            "pending_user_action": self.pending_user_action,
            "user_decision": self.user_decision,
            "market_context": self.market_context,
            "rounds": self.rounds,
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "status": self.status,
            "active_agent": self.active_agent,
            "logs": self.logs,
        }

    # Convenience for LangGraph TypedDict compatibility
    def as_langgraph_state(self) -> dict:
        return self.to_dict()

    @classmethod
    def from_dict(cls, d: dict) -> "NegotiationState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
