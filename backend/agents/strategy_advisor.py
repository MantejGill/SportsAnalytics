"""Strategy advisor — BATNA and walk-away calculations."""

from __future__ import annotations

from typing import Any


def compute_strategy(market_context: dict, club_constraints: dict | None = None) -> dict[str, Any]:
    """Return walk-away thresholds and BATNA for both sides.

    Parameters
    ----------
    market_context : dict
        Must contain p25_eur, median_eur, p75_eur, and optionally salary_range.
    club_constraints : dict, optional
        Must contain budget_eur if provided.

    Returns
    -------
    dict with club_walk_away_eur, player_walk_away_eur, batna, recommended_opening
    """
    p25 = market_context.get("p25_eur", 0)
    median = market_context.get("median_eur", 0)
    p75 = market_context.get("p75_eur", 0)
    predicted = market_context.get("predicted_value_eur", median)
    salary_range = market_context.get("salary_range", {})

    # Walk-away thresholds (for annual salary negotiation)
    mid_salary = salary_range.get("mid_eur", int(predicted * 0.10))
    low_salary = salary_range.get("low_eur", int(predicted * 0.07))
    high_salary = salary_range.get("high_eur", int(predicted * 0.14))

    club_walk_away_salary = int(high_salary * 1.15)
    player_walk_away_salary = int(low_salary * 0.85)

    # Transfer fee walk-aways
    club_walk_away_fee = int(p75 * 1.15)
    player_walk_away_fee = int(p25 * 0.85)

    # BATNA (Best Alternative To Negotiated Agreement)
    club_batna = {
        "description": "Sign an alternative player at or below market median",
        "estimated_cost_eur": int(median * 0.90),
        "estimated_salary_eur": mid_salary,
    }
    player_batna = {
        "description": "Accept offer from another club at market rate",
        "estimated_value_eur": median,
        "estimated_salary_eur": mid_salary,
    }

    # Budget constraint adjustment
    if club_constraints:
        budget = club_constraints.get("budget_eur", 0)
        if budget and budget < club_walk_away_salary:
            club_walk_away_salary = budget

    # Recommended opening positions
    club_opening_salary = int(low_salary * 1.05)
    player_opening_salary = int(high_salary * 0.95)

    return {
        "club_walk_away_salary_eur": club_walk_away_salary,
        "player_walk_away_salary_eur": player_walk_away_salary,
        "club_walk_away_fee_eur": club_walk_away_fee,
        "player_walk_away_fee_eur": player_walk_away_fee,
        "club_batna": club_batna,
        "player_batna": player_batna,
        "recommended_opening": {
            "club_salary_eur": club_opening_salary,
            "player_salary_eur": player_opening_salary,
        },
        "zone_of_possible_agreement": {
            "salary_low_eur": player_walk_away_salary,
            "salary_high_eur": club_walk_away_salary,
            "fee_low_eur": player_walk_away_fee,
            "fee_high_eur": club_walk_away_fee,
        },
    }
