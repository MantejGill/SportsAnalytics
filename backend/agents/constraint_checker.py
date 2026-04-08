"""Four-layer constraint checker for term sheets."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from negotiation.term_sheet import TermSheet

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "league_rules.json"
_RULES: dict | None = None


def _load_rules() -> dict:
    global _RULES
    if _RULES is not None:
        return _RULES
    if _RULES_PATH.exists():
        with open(_RULES_PATH, "r") as f:
            _RULES = json.load(f)
    else:
        _RULES = {}
    return _RULES


def check_constraints(
    term_sheet: dict,
    market_context: dict | None,
    rounds: list[dict],
    current_round: int,
    club_constraints: dict | None = None,
    market_tolerance_low: float = 0.5,
    market_tolerance_high: float = 2.0,
) -> dict[str, Any]:
    """Run all four validation layers.

    Returns
    -------
    dict with keys: valid (bool), violations (list[str]), warnings (list[str]),
    suggested_fix (dict | None).
    """
    violations: list[str] = []
    warnings: list[str] = []
    suggested_fix: dict | None = None
    rules = _load_rules().get("fifa_regulations", {})

    # ------------------------------------------------------------------
    # Layer 0 — Format
    # ------------------------------------------------------------------
    required_fields = [
        "player_name",
        "position",
        "base_salary_eur",
        "contract_years",
    ]
    for fld in required_fields:
        if fld not in term_sheet:
            violations.append(f"L0-FORMAT: missing required field '{fld}'")

    numeric_fields = [
        "base_salary_eur",
        "signing_bonus_eur",
        "performance_bonus_eur",
        "contract_years",
        "release_clause_eur",
        "image_rights_pct",
    ]
    for fld in numeric_fields:
        val = term_sheet.get(fld)
        if val is not None and not isinstance(val, (int, float)):
            violations.append(f"L0-FORMAT: '{fld}' must be a number, got {type(val).__name__}")

    # ------------------------------------------------------------------
    # Layer 1 — Contract sanity
    # ------------------------------------------------------------------
    years = term_sheet.get("contract_years", 0)
    min_yrs = rules.get("min_contract_years", 1)
    max_yrs = rules.get("max_contract_years", 5)
    if not (min_yrs <= years <= max_yrs):
        violations.append(
            f"L1-SANITY: contract_years={years} outside allowed range [{min_yrs}, {max_yrs}]"
        )

    for fld in ("base_salary_eur", "signing_bonus_eur", "performance_bonus_eur", "release_clause_eur"):
        val = term_sheet.get(fld, 0)
        if isinstance(val, (int, float)) and val < 0:
            violations.append(f"L1-SANITY: {fld} must be non-negative, got {val}")

    img_pct = term_sheet.get("image_rights_pct", 0)
    max_img = rules.get("max_image_rights_pct", 50)
    if isinstance(img_pct, (int, float)) and img_pct > max_img:
        violations.append(f"L1-SANITY: image_rights_pct={img_pct} exceeds max {max_img}")

    base = term_sheet.get("base_salary_eur", 0)
    perf = term_sheet.get("performance_bonus_eur", 0)
    max_perf_pct = rules.get("max_performance_bonus_pct", 30)
    if isinstance(base, (int, float)) and isinstance(perf, (int, float)) and base > 0:
        if perf > base * max_perf_pct / 100:
            warnings.append(
                f"L1-SANITY: performance_bonus_eur ({perf}) exceeds {max_perf_pct}% of base salary ({base})"
            )

    signing = term_sheet.get("signing_bonus_eur", 0)
    max_sign_pct = rules.get("max_signing_bonus_pct", 25)
    if isinstance(base, (int, float)) and isinstance(signing, (int, float)) and base > 0:
        if signing > base * max_sign_pct / 100:
            warnings.append(
                f"L1-SANITY: signing_bonus_eur ({signing}) exceeds {max_sign_pct}% of base salary ({base})"
            )

    release = term_sheet.get("release_clause_eur", 0)
    max_rc_mult = rules.get("max_release_clause_multiplier", 10)
    if isinstance(base, (int, float)) and isinstance(release, (int, float)) and base > 0 and release > 0:
        if release > base * max_rc_mult:
            warnings.append(
                f"L1-SANITY: release_clause_eur ({release}) exceeds {max_rc_mult}x annual salary"
            )

    # Verify total computation
    if isinstance(base, (int, float)) and isinstance(years, int) and years > 0:
        expected_total = base * years + term_sheet.get("signing_bonus_eur", 0) + term_sheet.get("performance_bonus_eur", 0) * years
        given_total = term_sheet.get("total_value_eur")
        if given_total is not None and isinstance(given_total, (int, float)):
            if abs(given_total - expected_total) > 1:
                warnings.append(
                    f"L1-SANITY: total_value_eur mismatch: given {given_total}, expected {expected_total}"
                )

    # Budget check
    if club_constraints and isinstance(base, (int, float)):
        budget = club_constraints.get("budget_eur", 0)
        annual_cost = base + term_sheet.get("performance_bonus_eur", 0)
        if budget and annual_cost > budget:
            violations.append(
                f"L1-SANITY: annual cost ({annual_cost}) exceeds club budget ({budget})"
            )

    # ------------------------------------------------------------------
    # Layer 2 — Market realism
    # ------------------------------------------------------------------
    if market_context and isinstance(base, (int, float)):
        predicted = market_context.get("predicted_value_eur", 0)
        salary_range = market_context.get("salary_range", {})
        mid_salary = salary_range.get("mid_eur", predicted * 0.10) if salary_range else predicted * 0.10

        if mid_salary and mid_salary > 0:
            low_bound = mid_salary * market_tolerance_low
            high_bound = mid_salary * market_tolerance_high
            if base < low_bound:
                warnings.append(
                    f"L2-MARKET: base_salary_eur ({base}) is below {market_tolerance_low}x market mid ({int(mid_salary)})"
                )
                suggested_fix = {
                    "base_salary_eur": int(mid_salary * 0.85),
                    "reason": "adjusted to 85% of market mid salary",
                }
            elif base > high_bound:
                warnings.append(
                    f"L2-MARKET: base_salary_eur ({base}) exceeds {market_tolerance_high}x market mid ({int(mid_salary)})"
                )
                suggested_fix = {
                    "base_salary_eur": int(mid_salary * 1.15),
                    "reason": "adjusted to 115% of market mid salary",
                }

    # ------------------------------------------------------------------
    # Layer 3 — Protocol
    # ------------------------------------------------------------------
    if len(rounds) >= 2:
        last_two = rounds[-2:]
        # Check for repeated identical offers from the same side
        if (
            last_two[0].get("side") == last_two[1].get("side")
            and last_two[0].get("term_sheet") == last_two[1].get("term_sheet")
            and last_two[0].get("term_sheet")  # not both empty
        ):
            violations.append("L3-PROTOCOL: repeated identical offer from the same side")

    if current_round < 0:
        violations.append(f"L3-PROTOCOL: invalid round counter {current_round}")

    valid = len(violations) == 0

    return {
        "valid": valid,
        "violations": violations,
        "warnings": warnings,
        "suggested_fix": suggested_fix,
    }
