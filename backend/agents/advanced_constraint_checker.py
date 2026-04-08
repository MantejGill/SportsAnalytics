"""Smriti's full constraint checker — FIFA rules + project policy + round/history validation.

Drop-in replacement for the default four-layer constraint checker.
All validation functions are ported directly from constraint_checker_final.ipynb.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load rule files
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_OFFICIAL_RULES: dict | None = None
_PROJECT_RULES: dict | None = None


def _load_official_rules() -> dict:
    global _OFFICIAL_RULES
    if _OFFICIAL_RULES is None:
        path = _DATA_DIR / "official_fifa_rules.json"
        with open(path, "r") as f:
            _OFFICIAL_RULES = json.load(f)
    return _OFFICIAL_RULES


def _load_project_rules() -> dict:
    """Load project policy rules from JSON. Returns a fresh deep copy each time
    so that per-negotiation dynamic overrides don't leak across sessions."""
    global _PROJECT_RULES
    if _PROJECT_RULES is None:
        path = _DATA_DIR / "project_policy_rules.json"
        with open(path, "r") as f:
            _PROJECT_RULES = json.load(f)
    import copy
    return copy.deepcopy(_PROJECT_RULES)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "player_name",
    "club_name",
    "base_salary_eur",
    "contract_years",
    "guaranteed_amount_eur",
]

NUMERIC_FIELDS = [
    "base_salary_eur",
    "contract_years",
    "signing_bonus_eur",
    "performance_bonus_eur",
    "guaranteed_amount_eur",
    "release_clause_eur",
    "agent_fee_eur",
    "sell_on_clause_percent",
    "predicted_market_value_eur",
    "predicted_salary_eur",
    "player_age",
    "months_to_contract_expiry",
    "annual_remuneration_usd_for_agent_cap_check",
    "annual_remuneration_for_agent_fee_base_eur",
    "transfer_compensation_eur",
    "loan_duration_years",
]

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def is_number(x: Any) -> bool:
    """Returns True for regular numeric values and False for bools / NaNs / None."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not math.isnan(float(x))


def safe_float(x: Any, default: float = 0.0) -> float:
    """Converts numeric-looking inputs safely and falls back to a default."""
    if x is None:
        return default
    if is_number(x):
        return float(x)
    return default


def add_issue(rule_id: str, severity: str, source: str, message: str) -> Dict[str, str]:
    """Creates one standard validation message."""
    return {
        "rule_id": rule_id,
        "severity": severity,
        "source": source,
        "message": message,
    }


def compute_total_contract_value(offer: Dict[str, Any]) -> float:
    """A simple total value proxy used by several rules.

    NOTE: performance_bonus_eur is treated as an *annual* figure (paid per year),
    matching the TermSheet model used throughout the negotiation pipeline.
    """
    base = safe_float(offer.get("base_salary_eur"), 0.0)
    years = safe_float(offer.get("contract_years"), 0.0)
    signing = safe_float(offer.get("signing_bonus_eur"), 0.0)
    performance = safe_float(offer.get("performance_bonus_eur"), 0.0)
    return base * years + signing + performance * years


def get_reference_value_eur(offer: Dict[str, Any], project_rules: Dict[str, Any]) -> float:
    """Uses the configured priority order for valuation inputs."""
    fields = project_rules["market_rules"]["reference_value_field_priority"]
    for field in fields:
        if field in offer and offer[field] is not None:
            value = safe_float(offer[field], 0.0)
            if value > 0:
                return value
    return 0.0


def get_market_band(offer: Dict[str, Any], project_rules: Dict[str, Any]):
    """Returns the acceptable valuation band for market-alignment checks."""
    reference_value = get_reference_value_eur(offer, project_rules)
    lower_mult = project_rules["market_rules"].get("market_value_lower_multiplier", 0.4)
    upper_mult = project_rules["market_rules"].get("market_value_upper_multiplier", 1.6)
    return lower_mult * reference_value, upper_mult * reference_value


def get_agent_fee_cap_fraction(offer: Dict[str, Any], official_rules: Dict[str, Any]) -> Optional[float]:
    """Returns the relevant FIFA fee cap fraction if enough fields are present."""
    fee_rules = official_rules["agent_fee_rules"]
    annual_remuneration_usd = safe_float(offer.get("annual_remuneration_usd_for_agent_cap_check"), 0.0)
    representation_type = offer.get("agent_representation_type")

    if annual_remuneration_usd <= 0 or representation_type is None:
        return None

    le_200k = annual_remuneration_usd <= 200000

    if representation_type == "individual":
        return fee_rules["individual_fee_pct_if_remuneration_le_200k_usd"] if le_200k else fee_rules["individual_fee_pct_if_remuneration_gt_200k_usd"]
    if representation_type == "engaging_entity":
        return fee_rules["engaging_entity_fee_pct_if_remuneration_le_200k_usd"] if le_200k else fee_rules["engaging_entity_fee_pct_if_remuneration_gt_200k_usd"]
    if representation_type == "dual_representation":
        return fee_rules["dual_representation_fee_pct_if_remuneration_le_200k_usd"] if le_200k else fee_rules["dual_representation_fee_pct_if_remuneration_gt_200k_usd"]
    if representation_type == "releasing_entity":
        return fee_rules["releasing_entity_transfer_comp_fee_pct"]

    return None


def canonicalize_offer(offer: Dict[str, Any]) -> Dict[str, Any]:
    """Keeps only negotiation-relevant financial terms for repeat detection.

    NOTE: ``guaranteed_amount_eur`` is excluded because it is a derived value
    (base * years) that the wrapper injects only into the current offer, not into
    history entries.  Including it would prevent identical raw offers from matching.
    """
    keys = [
        "base_salary_eur",
        "contract_years",
        "signing_bonus_eur",
        "performance_bonus_eur",
        "release_clause_eur",
        "agent_fee_eur",
        "sell_on_clause_percent",
    ]
    return {k: offer.get(k, None) for k in keys}


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


def validate_schema(offer: Dict[str, Any]) -> List[Dict[str, str]]:
    """Checks basic required fields, numeric types, and simple ranges."""
    issues: list[dict[str, str]] = []

    for field in REQUIRED_FIELDS:
        if field not in offer:
            issues.append(add_issue(
                "MISSING_REQUIRED_FIELD",
                "error",
                "schema",
                f"Missing required field: {field}",
            ))

    for field in NUMERIC_FIELDS:
        if field in offer and offer[field] is not None and not is_number(offer[field]):
            issues.append(add_issue(
                "INVALID_NUMERIC_TYPE",
                "error",
                "schema",
                f"{field} must be numeric",
            ))

    for field in NUMERIC_FIELDS:
        if field in offer and offer[field] is not None and is_number(offer[field]):
            if field != "sell_on_clause_percent" and float(offer[field]) < 0:
                issues.append(add_issue(
                    "NEGATIVE_VALUE",
                    "error",
                    "schema",
                    f"{field} cannot be negative",
                ))

    years = offer.get("contract_years")
    if years is not None and is_number(years):
        years = float(years)
        if int(years) != years:
            issues.append(add_issue(
                "NON_INTEGER_CONTRACT_YEARS",
                "error",
                "schema",
                "contract_years must be an integer",
            ))

    pct = offer.get("sell_on_clause_percent")
    if pct is not None and is_number(pct):
        pct = float(pct)
        if not (0 <= pct <= 100):
            issues.append(add_issue(
                "SELL_ON_PERCENT_OUT_OF_RANGE",
                "error",
                "schema",
                "sell_on_clause_percent must be between 0 and 100",
            ))

    return issues


def validate_official_fifa_rules(offer: Dict[str, Any], official_rules: Dict[str, Any]) -> List[Dict[str, str]]:
    """Checks official football rules that can be validated from structured inputs."""
    issues: list[dict[str, str]] = []
    contract_rules = official_rules["contract_rules"]
    loan_rules = official_rules["loan_rules"]
    minor_rules = official_rules["minor_rules"]

    contract_years = safe_float(offer.get("contract_years"), 0.0)
    player_age = safe_float(offer.get("player_age"), -1)
    months_to_expiry = safe_float(offer.get("months_to_contract_expiry"), -1)

    # Contract length limits
    if player_age >= 0 and player_age < 18:
        if contract_years > contract_rules["max_contract_years_under_18"]:
            issues.append(add_issue(
                "MAX_CONTRACT_YEARS_UNDER_18_FIFA",
                "error",
                "official_fifa_rules",
                f"Under-18 player contract exceeds FIFA limit of {contract_rules['max_contract_years_under_18']} years",
            ))
    else:
        if contract_years > contract_rules["max_contract_years_default"]:
            issues.append(add_issue(
                "MAX_CONTRACT_YEARS_FIFA",
                "error",
                "official_fifa_rules",
                f"contract_years exceeds FIFA default maximum of {contract_rules['max_contract_years_default']} years",
            ))

    # Pre-contract window
    is_currently_under_contract = offer.get("is_currently_under_contract")
    if is_currently_under_contract is True and months_to_expiry >= 0:
        if months_to_expiry > contract_rules["can_sign_precontract_if_contract_expires_within_months"]:
            issues.append(add_issue(
                "PRECONTRACT_WINDOW_VIOLATION_FIFA",
                "warning",
                "official_fifa_rules",
                f"Player appears outside FIFA's {contract_rules['can_sign_precontract_if_contract_expires_within_months']}-month pre-contract window",
            ))

    # Current club notification
    if offer.get("requires_current_club_notification") is True and offer.get("current_club_notified_in_writing") is False:
        issues.append(add_issue(
            "CURRENT_CLUB_NOTIFICATION_MISSING_FIFA",
            "warning",
            "official_fifa_rules",
            "Current club should be informed in writing before entering negotiations",
        ))

    # Medical exam condition
    if contract_rules["cannot_condition_validity_on_medical_exam"] and offer.get("contract_validity_conditioned_on_medical_exam") is True:
        issues.append(add_issue(
            "MEDICAL_EXAM_VALIDITY_CONDITION_FIFA",
            "error",
            "official_fifa_rules",
            "Contract validity cannot be conditioned on a successful medical examination",
        ))

    # Work permit condition
    if contract_rules["cannot_condition_validity_on_work_permit"] and offer.get("contract_validity_conditioned_on_work_permit") is True:
        issues.append(add_issue(
            "WORK_PERMIT_VALIDITY_CONDITION_FIFA",
            "error",
            "official_fifa_rules",
            "Contract validity cannot be conditioned on the grant of a work permit",
        ))

    # Unilateral termination during competition
    if official_rules["contract_rules"]["no_unilateral_termination_during_competition_period"]:
        if offer.get("unilateral_termination_attempted_during_competition_period") is True:
            issues.append(add_issue(
                "UNILATERAL_TERMINATION_DURING_COMPETITION_PERIOD_FIFA",
                "error",
                "official_fifa_rules",
                "A contract cannot be unilaterally terminated during a competition period",
            ))

    # Minor international transfer
    if minor_rules["international_transfer_under_18_prohibited_except_exceptions"]:
        if player_age >= 0 and player_age < 18 and offer.get("is_international_transfer") is True:
            if offer.get("minor_exception_applies") is not True:
                issues.append(add_issue(
                    "MINOR_INTERNATIONAL_TRANSFER_FIFA",
                    "error",
                    "official_fifa_rules",
                    "International transfer of an under-18 player requires a valid FIFA exception",
                ))

    # Loan rules
    if offer.get("is_loan") is True:
        loan_duration_years = safe_float(offer.get("loan_duration_years"), 0.0)

        if loan_duration_years > loan_rules["max_loan_duration_years"]:
            issues.append(add_issue(
                "MAX_LOAN_DURATION_FIFA",
                "error",
                "official_fifa_rules",
                f"Loan duration exceeds FIFA maximum of {loan_rules['max_loan_duration_years']} year",
            ))

        if offer.get("written_loan_agreement_present") is False:
            issues.append(add_issue(
                "WRITTEN_LOAN_AGREEMENT_REQUIRED_FIFA",
                "error",
                "official_fifa_rules",
                "Written loan agreement is required",
            ))

        if offer.get("loan_contract_with_new_club_present") is False:
            issues.append(add_issue(
                "LOAN_CONTRACT_WITH_NEW_CLUB_REQUIRED_FIFA",
                "error",
                "official_fifa_rules",
                "Separate player-new club contract is required for a loan",
            ))

        if loan_rules["subloan_prohibited"] and offer.get("is_subloan") is True:
            issues.append(add_issue(
                "SUBLOAN_PROHIBITED_FIFA",
                "error",
                "official_fifa_rules",
                "Sub-loans are prohibited",
            ))

    # Agent fee cap
    agent_fee = safe_float(offer.get("agent_fee_eur"), 0.0)
    cap_fraction = get_agent_fee_cap_fraction(offer, official_rules)

    if cap_fraction is not None:
        representation_type = offer.get("agent_representation_type")
        if representation_type == "releasing_entity":
            base_amount = safe_float(offer.get("transfer_compensation_eur"), 0.0)
        else:
            base_amount = safe_float(offer.get("annual_remuneration_for_agent_fee_base_eur"), 0.0)

        if base_amount > 0 and agent_fee > cap_fraction * base_amount:
            issues.append(add_issue(
                "AGENT_FEE_CAP_FIFA",
                "warning",
                "official_fifa_rules",
                f"agent_fee_eur appears above FIFA cap for representation type '{representation_type}'",
            ))

    return issues


def validate_project_policy_rules(offer: Dict[str, Any], project_rules: Dict[str, Any]) -> List[Dict[str, str]]:
    """Checks project-defined policies and market realism."""
    issues: list[dict[str, str]] = []
    policies = project_rules["negotiation_policies"]

    total_value = compute_total_contract_value(offer)
    guaranteed = safe_float(offer.get("guaranteed_amount_eur"), 0.0)
    signing_bonus = safe_float(offer.get("signing_bonus_eur"), 0.0)
    performance_bonus = safe_float(offer.get("performance_bonus_eur"), 0.0)
    release_clause = offer.get("release_clause_eur")
    base_salary = safe_float(offer.get("base_salary_eur"), 0.0)
    sell_on_clause_percent = safe_float(offer.get("sell_on_clause_percent"), 0.0)

    if guaranteed > total_value:
        issues.append(add_issue(
            "GUARANTEE_GT_TOTAL",
            "error",
            "project_policy_rules",
            "guaranteed_amount_eur exceeds total contract value",
        ))

    if signing_bonus > total_value:
        issues.append(add_issue(
            "SIGNING_BONUS_GT_TOTAL",
            "error",
            "project_policy_rules",
            "signing_bonus_eur exceeds total contract value",
        ))

    if release_clause is not None and is_number(release_clause) and float(release_clause) > 0:
        if float(release_clause) < guaranteed:
            issues.append(add_issue(
                "RELEASE_LT_GUARANTEE",
                "error",
                "project_policy_rules",
                "release_clause_eur cannot be lower than guaranteed_amount_eur",
            ))

    team_budget_cap = policies.get("team_budget_cap_eur")
    if team_budget_cap is not None and is_number(team_budget_cap) and total_value > team_budget_cap:
        issues.append(add_issue(
            "TEAM_BUDGET_CAP_EXCEEDED",
            "error",
            "project_policy_rules",
            f"total contract value exceeds team budget cap of {team_budget_cap:,.0f} EUR",
        ))

    player_min_salary = policies.get("player_min_salary_eur")
    if player_min_salary is not None and is_number(player_min_salary) and base_salary < player_min_salary:
        issues.append(add_issue(
            "SALARY_BELOW_PLAYER_MINIMUM",
            "warning",
            "project_policy_rules",
            f"base_salary_eur is below player minimum ask of {player_min_salary:,.0f} EUR",
        ))

    team_max_salary = policies.get("team_max_salary_eur")
    if team_max_salary is not None and is_number(team_max_salary) and base_salary > team_max_salary:
        issues.append(add_issue(
            "SALARY_ABOVE_TEAM_MAXIMUM",
            "warning",
            "project_policy_rules",
            f"base_salary_eur is above team maximum preferred offer of {team_max_salary:,.0f} EUR",
        ))

    max_sell_on_pct = policies.get("max_sell_on_clause_percent_preferred", 25)
    if sell_on_clause_percent > max_sell_on_pct:
        issues.append(add_issue(
            "SELL_ON_CLAUSE_TOO_HIGH",
            "warning",
            "project_policy_rules",
            f"sell_on_clause_percent exceeds preferred threshold of {max_sell_on_pct}%",
        ))

    perf_mult = policies.get("max_performance_bonus_multiple_of_base", 2.0)
    if base_salary > 0 and performance_bonus > perf_mult * base_salary:
        issues.append(add_issue(
            "PERFORMANCE_BONUS_TOO_HIGH",
            "warning",
            "project_policy_rules",
            "performance_bonus_eur is unusually high relative to base salary",
        ))

    reference_value = get_reference_value_eur(offer, project_rules)
    if reference_value <= 0:
        issues.append(add_issue(
            "MISSING_REFERENCE_MARKET_VALUE",
            "error",
            "project_policy_rules",
            "Either predicted_salary_eur or predicted_market_value_eur must be positive",
        ))
    else:
        lower_bound, upper_bound = get_market_band(offer, project_rules)
        if base_salary < lower_bound:
            issues.append(add_issue(
                "SALARY_BELOW_MARKET_RANGE",
                "warning",
                "project_policy_rules",
                f"base_salary_eur is below expected market range [{lower_bound:,.0f}, {upper_bound:,.0f}]",
            ))
        if base_salary > upper_bound:
            issues.append(add_issue(
                "SALARY_ABOVE_MARKET_RANGE",
                "warning",
                "project_policy_rules",
                f"base_salary_eur is above expected market range [{lower_bound:,.0f}, {upper_bound:,.0f}]",
            ))

    return issues


def validate_round_rules(
    round_state: Dict[str, Any],
    project_rules: Dict[str, Any],
    offer: Dict[str, Any] | None = None,
) -> List[Dict[str, str]]:
    """Checks whether the current negotiation step is legal."""
    issues: list[dict[str, str]] = []

    round_number = round_state.get("round_number")
    max_rounds = project_rules.get("max_rounds", 6)
    current_action = round_state.get("current_action")
    negotiation_status = round_state.get("negotiation_status", "ongoing")
    last_action = round_state.get("last_action")
    allowed_actions = set(project_rules.get("allowed_actions", []))

    if round_number is None:
        issues.append(add_issue(
            "MISSING_ROUND_NUMBER",
            "error",
            "project_policy_rules",
            "round_number is required",
        ))
    elif round_number > max_rounds:
        issues.append(add_issue(
            "MAX_ROUNDS_EXCEEDED",
            "error",
            "project_policy_rules",
            "round_number exceeds max_rounds",
        ))

    if current_action not in allowed_actions:
        issues.append(add_issue(
            "INVALID_ACTION",
            "error",
            "project_policy_rules",
            f"current_action must be one of {sorted(allowed_actions)}",
        ))

    if negotiation_status != "ongoing":
        issues.append(add_issue(
            "NEGOTIATION_ALREADY_CLOSED",
            "error",
            "project_policy_rules",
            f"Negotiation is already {negotiation_status}; no further rounds allowed",
        ))

    if current_action == "counter" and offer is None:
        issues.append(add_issue(
            "COUNTER_REQUIRES_OFFER",
            "error",
            "project_policy_rules",
            "counter action requires an offer",
        ))

    if current_action == "accept" and offer is not None:
        issues.append(add_issue(
            "ACCEPT_SHOULD_NOT_INCLUDE_NEW_OFFER",
            "warning",
            "project_policy_rules",
            "accept action usually should not include a new modified offer",
        ))

    if last_action == "accept":
        issues.append(add_issue(
            "ACTION_AFTER_ACCEPT",
            "error",
            "project_policy_rules",
            "No further action allowed after accept",
        ))

    if last_action == "walk_away":
        issues.append(add_issue(
            "ACTION_AFTER_WALK_AWAY",
            "error",
            "project_policy_rules",
            "No further action allowed after walk_away",
        ))

    return issues


def validate_offer_history(
    current_offer: Dict[str, Any],
    offer_history: List[Dict[str, Any]],
    project_rules: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Flags negotiation stagnation when the same offer keeps reappearing."""
    issues: list[dict[str, str]] = []

    max_repeats = project_rules["negotiation_policies"].get("max_identical_offer_repeats", 2)
    current_canonical = canonicalize_offer(current_offer)
    repeat_count = 0

    for prev_offer in offer_history:
        if canonicalize_offer(prev_offer) == current_canonical:
            repeat_count += 1

    if repeat_count >= max_repeats:
        issues.append(add_issue(
            "IDENTICAL_OFFER_REPEATED",
            "warning",
            "project_policy_rules",
            f"Current offer has already appeared {repeat_count} time(s), which suggests negotiation stagnation",
        ))

    return issues


def validate_side_specific(
    round_state: Dict[str, Any],
    offer: Dict[str, Any],
    project_rules: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Adds side-specific logic without repeating general warnings."""
    issues: list[dict[str, str]] = []

    current_side = round_state.get("current_side")
    guaranteed = safe_float(offer.get("guaranteed_amount_eur"), 0.0)
    base_salary = safe_float(offer.get("base_salary_eur"), 0.0)

    if current_side == "player":
        if guaranteed < base_salary:
            issues.append(add_issue(
                "PLAYER_SIDE_LOW_GUARANTEE",
                "warning",
                "project_policy_rules",
                "Player-side offer has guaranteed amount lower than one year of base salary",
            ))

    return issues


# ---------------------------------------------------------------------------
# Top-level orchestrators (from notebook)
# ---------------------------------------------------------------------------


def validate_offer(
    offer: Dict[str, Any],
    official_rules: Dict[str, Any],
    project_rules: Dict[str, Any],
) -> Dict[str, Any]:
    """Runs all offer-level checks and returns a structured result."""
    issues: list[dict[str, str]] = []
    issues.extend(validate_schema(offer))
    issues.extend(validate_official_fifa_rules(offer, official_rules))
    issues.extend(validate_project_policy_rules(offer, project_rules))

    errors = [x for x in issues if x["severity"] == "error"]
    warnings = [x for x in issues if x["severity"] == "warning"]

    return {
        "valid": len(errors) == 0,
        "num_errors": len(errors),
        "num_warnings": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "derived": {
            "reference_value_eur": get_reference_value_eur(offer, project_rules),
            "total_contract_value_eur": compute_total_contract_value(offer),
        },
    }


def validate_round_and_offer(
    round_state: Dict[str, Any],
    offer: Dict[str, Any],
    official_rules: Dict[str, Any],
    project_rules: Dict[str, Any],
    offer_history: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Runs the full per-round constraint checker."""
    issues: list[dict[str, str]] = []
    offer_history = offer_history or []

    issues.extend(validate_round_rules(round_state, project_rules, offer))

    offer_result = validate_offer(offer, official_rules, project_rules)
    issues.extend(offer_result["errors"])
    issues.extend(offer_result["warnings"])

    issues.extend(validate_offer_history(offer, offer_history, project_rules))
    issues.extend(validate_side_specific(round_state, offer, project_rules))

    errors = [x for x in issues if x["severity"] == "error"]
    warnings = [x for x in issues if x["severity"] == "warning"]

    return {
        "valid": len(errors) == 0,
        "num_errors": len(errors),
        "num_warnings": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "derived": offer_result["derived"],
    }


# ---------------------------------------------------------------------------
# Wrapper matching existing constraint checker interface
# ---------------------------------------------------------------------------


def check_constraints_advanced(
    term_sheet: dict,
    market_context: dict | None,
    rounds: list[dict],
    current_round: int,
    club_constraints: dict | None = None,
    **kwargs: Any,
) -> dict:
    """Smriti's full constraint checker -- drop-in replacement.

    Converts the Auto-Negotiate term_sheet / rounds format into the offer /
    round_state format expected by Smriti's validators, then converts the
    results back into the standard ``{valid, violations, warnings, suggested_fix}``
    dict consumed by the rest of the pipeline.
    """
    official_rules = _load_official_rules()
    project_rules = _load_project_rules()

    # --- Dynamic overrides from negotiation context -----------------------
    # The static project_policy_rules.json has null placeholders for caps
    # that should be derived from the actual negotiation's club constraints.
    if club_constraints:
        budget = club_constraints.get("budget_eur", 0)
        if budget:
            policies = project_rules.get("negotiation_policies", {})
            if policies.get("team_budget_cap_eur") is None:
                policies["team_budget_cap_eur"] = budget * safe_float(
                    club_constraints.get("max_years", 5), 5.0
                )
            if policies.get("team_max_salary_eur") is None:
                policies["team_max_salary_eur"] = budget
            if policies.get("player_min_salary_eur") is None:
                walk_away = club_constraints.get("walk_away_threshold_eur", 0)
                if walk_away:
                    policies["player_min_salary_eur"] = walk_away

    # --- Build the offer dict from our term_sheet --------------------------
    offer: Dict[str, Any] = dict(term_sheet)  # shallow copy

    # Inject market prediction if available
    if market_context:
        if "predicted_market_value_eur" not in offer and "predicted_value_eur" in market_context:
            offer["predicted_market_value_eur"] = market_context["predicted_value_eur"]
        salary_range = market_context.get("salary_range", {})
        if "predicted_salary_eur" not in offer and salary_range:
            offer["predicted_salary_eur"] = salary_range.get("mid_eur", 0)

    # Ensure required fields have sensible defaults from term_sheet aliases
    if "club_name" not in offer:
        offer["club_name"] = offer.get("club", "unknown")
    if "guaranteed_amount_eur" not in offer:
        # Fallback: use base * years as guarantee proxy
        base = safe_float(offer.get("base_salary_eur"), 0.0)
        years = safe_float(offer.get("contract_years"), 0.0)
        offer["guaranteed_amount_eur"] = base * years

    # --- Determine side and action from the round that produced this term sheet
    current_side = "club"
    current_action = "counter"
    if rounds:
        # The term sheet being checked belongs to the last round appended
        last_round = rounds[-1]
        current_side = last_round.get("side", "club")
        raw_action = last_round.get("action", "COUNTER")
        current_action = raw_action.lower()  # Smriti uses lowercase

    # --- Build round_state from our round data ----------------------------
    last_action = None
    if len(rounds) >= 2:
        prev_round = rounds[-2]
        raw_last = prev_round.get("action", "")
        last_action = raw_last.lower() if raw_last else None

    round_state: Dict[str, Any] = {
        "round_number": current_round,
        "current_side": current_side,
        "last_action": last_action,
        "current_action": current_action,
        "negotiation_status": "ongoing",
    }

    # Build offer history from previous rounds (exclude current)
    offer_history: list[dict] = []
    for rnd in rounds[:-1] if rounds else []:
        ts = rnd.get("term_sheet", rnd.get("offer", {}))
        if ts:
            offer_history.append(ts)

    # --- Run Smriti's full validator --------------------------------------
    result = validate_round_and_offer(
        round_state, offer, official_rules, project_rules, offer_history,
    )

    # --- Convert to our standard format -----------------------------------
    violations = [issue["message"] for issue in result.get("errors", [])]
    warnings = [issue["message"] for issue in result.get("warnings", [])]

    # Build a suggested fix if salary is out of market range
    suggested_fix = None
    for issue in result.get("errors", []) + result.get("warnings", []):
        if issue["rule_id"] in ("SALARY_BELOW_MARKET_RANGE", "SALARY_ABOVE_MARKET_RANGE"):
            ref = result.get("derived", {}).get("reference_value_eur", 0)
            if ref > 0:
                suggested_fix = {
                    "base_salary_eur": int(ref),
                    "reason": f"adjusted to reference market value ({ref:,.0f} EUR)",
                }
                break

    return {
        "valid": result["valid"],
        "violations": violations,
        "warnings": warnings,
        "suggested_fix": suggested_fix,
    }
