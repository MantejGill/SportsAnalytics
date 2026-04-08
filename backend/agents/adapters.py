"""Adapter interfaces for plugging in teammate code (Abdullah's ML model, Smriti's constraint checker)."""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class IMarketPredictor(ABC):
    """Interface for market value prediction. Abdullah's model implements this."""
    @abstractmethod
    def predict(self, player_profile: dict) -> dict:
        """Returns market_context dict with predicted_value_eur, p25_eur, median_eur, p75_eur, salary_range, comparables."""
        ...

class IConstraintChecker(ABC):
    """Interface for constraint checking. Smriti's checker implements this."""
    @abstractmethod
    def check(self, term_sheet: dict, market_context: dict, rounds: list, current_round: int, club_constraints: dict) -> dict:
        """Returns {valid, violations, warnings, suggested_fix}."""
        ...

class DefaultMarketPredictor(IMarketPredictor):
    """Default implementation using sample_players.json."""
    def predict(self, player_profile: dict) -> dict:
        from agents.market_predictor import predict_market_value
        return predict_market_value(player_profile)

class DefaultConstraintChecker(IConstraintChecker):
    """Default implementation using our 4-layer checker."""
    def check(self, term_sheet, market_context, rounds, current_round, club_constraints) -> dict:
        from agents.constraint_checker import check_constraints
        return check_constraints(term_sheet, market_context, rounds, current_round, club_constraints)


# ---------------------------------------------------------------------------
# Smriti's constraint checker adapter
# ---------------------------------------------------------------------------

class SmritiConstraintChecker(IConstraintChecker):
    """Smriti's FIFA + project-policy constraint checker.

    Falls back to the default 4-layer checker if Smriti's code raises an
    unexpected exception.
    """

    def check(self, term_sheet, market_context, rounds, current_round, club_constraints) -> dict:
        try:
            from agents.smriti_constraint_checker import check_constraints_smriti
            return check_constraints_smriti(
                term_sheet, market_context, rounds, current_round, club_constraints,
            )
        except Exception as exc:
            logger.warning("SmritiConstraintChecker falling back to default: %s", exc, exc_info=True)
            return DefaultConstraintChecker().check(
                term_sheet, market_context, rounds, current_round, club_constraints,
            )


# ---------------------------------------------------------------------------
# Abdullah's ML predictor adapter (re-exported from abdullah_predictor.py)
# ---------------------------------------------------------------------------

class AbdullahPredictor(IMarketPredictor):
    """Abdullah's XGBoost market value predictor.

    Falls back to the default predictor for players not in the CSV or if the
    model file is missing.
    """

    def predict(self, player_profile: dict) -> dict:
        try:
            from agents.abdullah_predictor import predict_market_value_ml
            return predict_market_value_ml(player_profile)
        except Exception as exc:
            logger.warning("AbdullahPredictor falling back to default: %s", exc)
            return DefaultMarketPredictor().predict(player_profile)


# --- Singleton instances (swap these when integrating teammate code) ---
_predictor: IMarketPredictor = DefaultMarketPredictor()
_checker: IConstraintChecker = DefaultConstraintChecker()

def get_predictor() -> IMarketPredictor:
    return _predictor

def set_predictor(p: IMarketPredictor):
    global _predictor
    _predictor = p

def get_checker() -> IConstraintChecker:
    return _checker

def set_checker(c: IConstraintChecker):
    global _checker
    _checker = c
