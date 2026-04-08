"""Term-sheet Pydantic models used by both agents."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, computed_field, model_validator


class TermSheet(BaseModel):
    """A single contract offer / counter-offer."""

    player_name: str
    position: str
    base_salary_eur: int
    signing_bonus_eur: int = 0
    performance_bonus_eur: int = 0
    contract_years: int
    option_year: bool = False
    release_clause_eur: int = 0
    image_rights_pct: int = 0
    no_trade_clause: bool = False

    @computed_field  # type: ignore[misc]
    @property
    def total_value_eur(self) -> int:
        return (
            self.base_salary_eur * self.contract_years
            + self.signing_bonus_eur
            + self.performance_bonus_eur * self.contract_years
        )

    @model_validator(mode="after")
    def _non_negative(self) -> "TermSheet":
        for fld in (
            "base_salary_eur",
            "signing_bonus_eur",
            "performance_bonus_eur",
            "contract_years",
            "release_clause_eur",
            "image_rights_pct",
        ):
            if getattr(self, fld) < 0:
                raise ValueError(f"{fld} must be non-negative")
        return self


class ActionType(str, Enum):
    PROPOSE = "PROPOSE"
    COUNTER = "COUNTER"
    ACCEPT = "ACCEPT"
    WALK_AWAY = "WALK_AWAY"


class TermSheetAction(BaseModel):
    """Wrapper returned by every agent: an action + optional term sheet."""

    action: ActionType
    term_sheet: Optional[TermSheet] = None
    reasoning: str

    @model_validator(mode="after")
    def _require_sheet_for_offers(self) -> "TermSheetAction":
        if self.action in (ActionType.PROPOSE, ActionType.COUNTER) and self.term_sheet is None:
            raise ValueError(f"term_sheet is required when action is {self.action.value}")
        return self
