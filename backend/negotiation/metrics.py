"""Validation metrics for completed (or in-progress) negotiations."""

from __future__ import annotations

from negotiation.state import NegotiationState


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division that returns default when denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def _get_final_salary(state: NegotiationState) -> float | None:
    """Extract the base_salary_eur from the last round's term sheet."""
    for r in reversed(state.rounds):
        ts = r.get("term_sheet", {})
        if ts and "base_salary_eur" in ts:
            return float(ts["base_salary_eur"])
    return None


def compute_market_realism(state: NegotiationState) -> float:
    """0-100 score: how close the final deal is to the market salary band.

    - If final salary is between p25 and p75 salary range: 100.
    - If within 2x of that range: proportional score.
    - Otherwise: 0.
    """
    final_salary = _get_final_salary(state)
    if final_salary is None or not state.market_context:
        return 0.0

    salary_range = state.market_context.get("salary_range", {})
    p25 = float(salary_range.get("low_eur", 0))
    p75 = float(salary_range.get("high_eur", 0))

    if p25 == 0 and p75 == 0:
        return 0.0

    # Inside the band -> 100
    if p25 <= final_salary <= p75:
        return 100.0

    band_width = p75 - p25
    if band_width <= 0:
        return 100.0 if final_salary == p25 else 0.0

    # Below band
    if final_salary < p25:
        distance = p25 - final_salary
        max_tolerable = band_width  # 1x band width below p25
        if distance <= max_tolerable:
            return max(0.0, 100.0 * (1.0 - distance / max_tolerable))
        return 0.0

    # Above band
    distance = final_salary - p75
    max_tolerable = band_width  # 1x band width above p75
    if distance <= max_tolerable:
        return max(0.0, 100.0 * (1.0 - distance / max_tolerable))
    return 0.0


def compute_outcome_quality_club(state: NegotiationState) -> float:
    """0-100 score for the club.

    quality = (budget - final_salary) / (budget - p25)
    Higher is better for the club (got the player cheaper).
    """
    final_salary = _get_final_salary(state)
    if final_salary is None:
        return 0.0

    budget = float(state.club_constraints.get("budget_eur", 0))
    salary_range = (state.market_context or {}).get("salary_range", {})
    p25 = float(salary_range.get("low_eur", 0))

    if budget <= 0 or budget <= p25:
        return 50.0  # can't compute meaningfully

    score = _safe_div(budget - final_salary, budget - p25, 0.5) * 100.0
    return max(0.0, min(100.0, score))


def compute_outcome_quality_player(state: NegotiationState) -> float:
    """0-100 score for the player.

    quality = (final_salary - walk_away) / (p75 - walk_away)
    Higher is better for the player (got a bigger salary).
    """
    final_salary = _get_final_salary(state)
    if final_salary is None:
        return 0.0

    walk_away = float(state.walk_away_threshold_eur or 0)
    salary_range = (state.market_context or {}).get("salary_range", {})
    p75 = float(salary_range.get("high_eur", 0))

    if p75 <= walk_away:
        return 50.0  # can't compute meaningfully

    score = _safe_div(final_salary - walk_away, p75 - walk_away, 0.5) * 100.0
    return max(0.0, min(100.0, score))


def compute_efficiency(state: NegotiationState) -> float:
    """0-1 score. More efficient = fewer rounds used.

    efficiency = 1.0 - (rounds_used / max_rounds)
    """
    if state.max_rounds <= 0:
        return 0.0
    return 1.0 - (state.current_round / state.max_rounds)


def compute_compliance_rate(state: NegotiationState) -> float:
    """0-1 score. Fraction of rounds with zero constraint violations."""
    if not state.rounds:
        return 1.0

    clean = sum(
        1 for r in state.rounds
        if len(r.get("constraint_violations", [])) == 0
    )
    return clean / len(state.rounds)


def _extract_salaries_by_side(state: NegotiationState, side: str) -> list[float]:
    """Return the sequence of base_salary_eur values for a given side."""
    salaries = []
    for r in state.rounds:
        if r.get("side") != side:
            continue
        ts = r.get("term_sheet", {})
        if ts and "base_salary_eur" in ts:
            salaries.append(float(ts["base_salary_eur"]))
    return salaries


def compute_concession_rate(state: NegotiationState, side: str) -> float:
    """Average absolute salary movement per round for the given side.

    Returns EUR amount (not percentage) — divide by a reference salary for pct.
    """
    salaries = _extract_salaries_by_side(state, side)
    if len(salaries) < 2:
        return 0.0
    movements = [abs(salaries[i] - salaries[i - 1]) for i in range(1, len(salaries))]
    return sum(movements) / len(movements)


def compute_concession_rate_pct(state: NegotiationState, side: str) -> float:
    """Average percentage salary movement per round for the given side."""
    salaries = _extract_salaries_by_side(state, side)
    if len(salaries) < 2:
        return 0.0
    pcts = []
    for i in range(1, len(salaries)):
        prev = salaries[i - 1]
        if prev > 0:
            pcts.append(abs(salaries[i] - prev) / prev * 100.0)
    return sum(pcts) / len(pcts) if pcts else 0.0


def compute_negotiation_metrics(state: NegotiationState) -> dict:
    """Compute all validation metrics for a negotiation session.

    Returns a dict with:
    - market_realism: 0-100
    - outcome_quality_club: 0-100
    - outcome_quality_player: 0-100
    - efficiency: 0-1
    - compliance_rate: 0-1
    - concession_rate_club: avg EUR movement per round
    - concession_rate_player: avg EUR movement per round
    - concession_rate_club_pct: avg % movement per round
    - concession_rate_player_pct: avg % movement per round
    - rounds_used: int
    - max_rounds: int
    - final_status: str
    - final_salary_eur: float or null
    """
    final_salary = _get_final_salary(state)

    return {
        "market_realism": round(compute_market_realism(state), 1),
        "outcome_quality_club": round(compute_outcome_quality_club(state), 1),
        "outcome_quality_player": round(compute_outcome_quality_player(state), 1),
        "efficiency": round(compute_efficiency(state), 3),
        "compliance_rate": round(compute_compliance_rate(state), 3),
        "concession_rate_club": round(compute_concession_rate(state, "club")),
        "concession_rate_player": round(compute_concession_rate(state, "player")),
        "concession_rate_club_pct": round(compute_concession_rate_pct(state, "club"), 1),
        "concession_rate_player_pct": round(compute_concession_rate_pct(state, "player"), 1),
        "rounds_used": state.current_round,
        "max_rounds": state.max_rounds,
        "final_status": state.status,
        "final_salary_eur": final_salary,
    }
