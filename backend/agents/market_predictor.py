"""Market predictor agent — returns market context for a player."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PLAYERS_CACHE: dict | None = None


def _load_players() -> dict:
    global _PLAYERS_CACHE
    if _PLAYERS_CACHE is not None:
        return _PLAYERS_CACHE

    path = _DATA_DIR / "sample_players.json"
    if not path.exists():
        logger.warning("sample_players.json not found at %s", path)
        _PLAYERS_CACHE = {}
        return _PLAYERS_CACHE

    with open(path, "r") as f:
        data = json.load(f)

    _PLAYERS_CACHE = {p["name"].lower(): p for p in data.get("players", [])}
    return _PLAYERS_CACHE


# ---- Position-based fallback estimates ----------------------------------

_POSITION_DEFAULTS: dict[str, dict] = {
    "ST": {"predicted_value_eur": 60_000_000, "p25_eur": 40_000_000, "median_eur": 55_000_000, "p75_eur": 75_000_000},
    "LW": {"predicted_value_eur": 55_000_000, "p25_eur": 35_000_000, "median_eur": 50_000_000, "p75_eur": 70_000_000},
    "RW": {"predicted_value_eur": 55_000_000, "p25_eur": 35_000_000, "median_eur": 50_000_000, "p75_eur": 70_000_000},
    "CM": {"predicted_value_eur": 50_000_000, "p25_eur": 30_000_000, "median_eur": 45_000_000, "p75_eur": 65_000_000},
    "CB": {"predicted_value_eur": 45_000_000, "p25_eur": 25_000_000, "median_eur": 40_000_000, "p75_eur": 55_000_000},
    "GK": {"predicted_value_eur": 30_000_000, "p25_eur": 15_000_000, "median_eur": 25_000_000, "p75_eur": 40_000_000},
}

_DEFAULT_FALLBACK = {
    "predicted_value_eur": 40_000_000,
    "p25_eur": 25_000_000,
    "median_eur": 38_000_000,
    "p75_eur": 55_000_000,
}


def _age_factor(age: int) -> float:
    """Multiplier that depreciates value for older / very young players."""
    if age <= 21:
        return 0.85
    if age <= 27:
        return 1.0
    if age <= 30:
        return 0.85
    if age <= 33:
        return 0.65
    return 0.45


def _estimate_from_position(position: str, age: int) -> dict:
    base = _POSITION_DEFAULTS.get(position.upper(), _DEFAULT_FALLBACK)
    factor = _age_factor(age)
    ctx = {k: int(v * factor) for k, v in base.items()}
    low = int(ctx["predicted_value_eur"] * 0.07)
    mid = int(ctx["predicted_value_eur"] * 0.10)
    high = int(ctx["predicted_value_eur"] * 0.14)
    ctx["salary_range"] = {"low_eur": low, "mid_eur": mid, "high_eur": high}
    ctx["comparables"] = []
    return ctx


# ---- Public API ---------------------------------------------------------


def predict_market_value(player_profile: dict) -> dict:
    """Return a market_context dict for the given player profile.

    Uses sample_players.json for known players, otherwise estimates by
    position and age.
    """
    name = player_profile.get("name", "").lower()
    players = _load_players()

    if name in players:
        ctx = players[name].get("market_context", {})
        logger.info("Market predictor: found %s in database", name)
        return ctx

    position = player_profile.get("position", "CM")
    age = player_profile.get("age", 25)
    logger.info(
        "Market predictor: estimating for unknown player (pos=%s, age=%d)",
        position,
        age,
    )
    return _estimate_from_position(position, age)
