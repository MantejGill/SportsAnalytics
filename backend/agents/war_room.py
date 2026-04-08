"""War Room — 5 advisory agents that analyze an incoming offer for the user."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.market_predictor import _load_players
from orchestrator.config import settings

if TYPE_CHECKING:
    from negotiation.state import NegotiationState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Comparables Analysis (deterministic — lookup from sample_players.json)
# ---------------------------------------------------------------------------

# Clubs considered top-tier for salary comparisons (exclude Saudi, MLS, etc.)
_TOP_TIER_CLUBS = {
    "arsenal", "manchester city", "manchester united", "liverpool", "chelsea",
    "tottenham", "newcastle", "aston villa", "west ham",  # EPL
    "real madrid", "barcelona", "atletico madrid", "real sociedad",  # La Liga
    "bayern munich", "borussia dortmund", "bayer leverkusen", "rb leipzig",  # Bundesliga
    "psg", "paris saint-germain",  # Ligue 1 elite
    "juventus", "inter milan", "ac milan", "napoli", "roma",  # Serie A
}

# Known non-top-tier clubs to explicitly exclude (avoids substring false positives)
_EXCLUDED_CLUBS = {
    "al-nassr", "al-hilal", "al-ahli", "al-ittihad",  # Saudi Pro League
    "inter miami", "la galaxy",  # MLS
    "galatasaray", "fenerbahce", "besiktas",  # Turkish Super Lig
}


def _is_top_tier_club(club: str) -> bool:
    """Return True if club is in a top-5 European league (not Saudi, MLS, Turkish, etc.)."""
    if not club:
        return False
    club_lower = club.lower().strip()
    # Explicit exclusion takes priority
    if any(exc in club_lower for exc in _EXCLUDED_CLUBS):
        return False
    return any(t in club_lower for t in _TOP_TIER_CLUBS)


def _get_median(values: list[float]) -> float:
    if not values:
        return 0
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def analyze_comparables(state: "NegotiationState") -> dict[str, Any]:
    """Find comparable players/deals from the database and format as analysis with citations."""
    market = state.market_context or {}
    player = state.player_profile
    salary_range = market.get("salary_range", {})
    player_name_lower = player.get("name", "").lower()
    player_age = player.get("age", 25)

    # Step 1: Always use the player's own curated comparables from sample_players.json first
    players_db = _load_players()
    own_entry = players_db.get(player_name_lower, {})
    own_comparables = own_entry.get("market_context", {}).get("comparables", [])

    # Step 2: If the predictor returned comparables, use those (already curated)
    predictor_comparables = [
        c for c in market.get("comparables", [])
        if c.get("name", "").lower() != player_name_lower  # exclude self
    ]

    # Merge: own_comparables takes priority, supplement with predictor's if needed
    raw_comparables = own_comparables if own_comparables else predictor_comparables

    # Step 3: Supplement with same-position players from DB if still sparse
    if len(raw_comparables) < 3:
        position = player.get("position", "CM")
        for pname, pdata in players_db.items():
            if pname == player_name_lower:
                continue
            if pdata.get("position") == position:
                for comp in pdata.get("market_context", {}).get("comparables", []):
                    raw_comparables.append(comp)

    # Step 4: Filter — top-tier clubs only, age within ±7 years, no self-references
    filtered = []
    seen_names: set[str] = set()
    for c in raw_comparables:
        cname = c.get("name", "").lower()
        if cname == player_name_lower:
            continue  # never use the player's own contract as comparable
        if cname in seen_names:
            continue  # deduplicate
        club = c.get("club", "")
        if club and not _is_top_tier_club(club):
            continue  # exclude Saudi, MLS, etc.
        age_at_signing = c.get("age_at_signing", 0)
        if age_at_signing and abs(age_at_signing - player_age) > 7:
            continue  # age bracket filter
        seen_names.add(cname)
        filtered.append(c)

    # Step 5: Outlier removal — drop salaries > 3x the preliminary median
    raw_salaries = [c.get("salary_eur", 0) for c in filtered if c.get("salary_eur")]
    if raw_salaries:
        prelim_median = _get_median(raw_salaries)
        if prelim_median > 0:
            filtered = [c for c in filtered if c.get("salary_eur", 0) <= prelim_median * 3]

    # Limit to 6 most relevant
    comparables = filtered[:6]

    # Step 6: Compute median (not mean) comparable salary
    comp_salaries = [c.get("salary_eur", 0) for c in comparables if c.get("salary_eur")]
    median_comp_salary = int(_get_median(comp_salaries)) if comp_salaries else 0

    # Build cited entries
    cited_comparables = []
    for c in comparables:
        source = c.get("source", "Transfermarkt")
        source_url = c.get("source_url", "https://www.transfermarkt.us/")
        year = c.get("year", "")
        club = c.get("club", "")
        cited_comparables.append({
            "name": c.get("name", "Unknown"),
            "salary_eur": c.get("salary_eur", 0),
            "club": club,
            "year": year,
            "age_at_signing": c.get("age_at_signing", 0),
            "transfer_fee_eur": c.get("transfer_fee_eur", 0),
            "source": source,
            "source_url": source_url,
            "citation": f"{c.get('name', '?')} — EUR {c.get('salary_eur', 0):,}/yr at {club} ({year}) [Source: {source}]"
        })

    range_basis = salary_range.get("basis", "Position-based estimate")
    tv_source = market.get("transfer_value_source", "Transfermarkt")
    tv_url = market.get("transfer_value_url", "https://www.transfermarkt.us/")

    return {
        "comparables": cited_comparables,
        "median_comparable_salary_eur": median_comp_salary,
        # Keep average_comparable_salary_eur for backwards compat but use median
        "average_comparable_salary_eur": median_comp_salary,
        "player_position": player.get("position", "Unknown"),
        "player_age": player_age,
        "market_salary_range": salary_range,
        "range_methodology": range_basis,
        "transfer_value_citation": f"Market value: EUR {market.get('predicted_value_eur', 0):,} [Source: {tv_source}]",
        "transfer_value_source": tv_source,
        "transfer_value_url": tv_url,
        "summary": (
            f"Found {len(cited_comparables)} comparable deals. "
            f"Median comparable salary: EUR {median_comp_salary:,}. "
            f"Market salary range: EUR {salary_range.get('low_eur', 0):,} - "
            f"EUR {salary_range.get('high_eur', 0):,}. "
            f"[Data: {tv_source}, Spotrac, Capology 2024-25]"
        ),
    }


# ---------------------------------------------------------------------------
# 2. Offer Analysis (deterministic — compute percentile and breakdown)
# ---------------------------------------------------------------------------

def analyze_offer(state: "NegotiationState") -> dict[str, Any]:
    """Break down the latest offer: salary vs market band percentile, components."""
    market = state.market_context or {}
    salary_range = market.get("salary_range", {})
    low = salary_range.get("low_eur", 0)
    mid = salary_range.get("mid_eur", 0)
    high = salary_range.get("high_eur", 0)

    # Get the latest offer (the AI opponent's most recent proposal)
    last_offer = _get_latest_opponent_offer(state)
    if not last_offer:
        return {"summary": "No offer to analyze yet.", "components": {}}

    term = last_offer.get("term_sheet", {})
    base = term.get("base_salary_eur", 0)
    signing = term.get("signing_bonus_eur", 0)
    perf = term.get("performance_bonus_eur", 0)
    years = term.get("contract_years", 1)
    total = base * years + signing + perf * years
    annual_total = base + perf + (signing / years if years > 0 else 0)

    # Compute percentile position
    percentile = 0
    if high > low and low > 0:
        percentile = int(((base - low) / (high - low)) * 100)
        percentile = max(0, min(100, percentile))

    # Position relative to market
    if mid > 0:
        vs_median_pct = round(((base - mid) / mid) * 100, 1)
    else:
        vs_median_pct = 0

    return {
        "base_salary_eur": base,
        "signing_bonus_eur": signing,
        "performance_bonus_eur": perf,
        "contract_years": years,
        "total_value_eur": total,
        "annual_total_eur": int(annual_total),
        "market_percentile": percentile,
        "vs_median_pct": vs_median_pct,
        "option_year": term.get("option_year", False),
        "release_clause_eur": term.get("release_clause_eur", 0),
        "image_rights_pct": term.get("image_rights_pct", 0),
        "no_trade_clause": term.get("no_trade_clause", False),
        "summary": (
            f"• Base salary: EUR {base:,}/yr — {'below market range' if base < low else f'{percentile}th percentile'}\n"
            f"• Total value: EUR {total:,} over {years} years\n"
            f"• vs Market median: {vs_median_pct:+.1f}% ({'Above' if vs_median_pct > 0 else 'Below'})\n"
            f"• Salary range: EUR {low:,} (low) / EUR {mid:,} (mid) / EUR {high:,} (high)\n"
            f"• Guaranteed: EUR {base * years + signing:,} ({round((base * years + signing) / total * 100) if total > 0 else 0}%) | Performance: EUR {perf * years:,} ({round(perf * years / total * 100) if total > 0 else 0}%)"
        ),
        "components": {
            "guaranteed": base * years + signing,
            "performance_based": perf * years,
            "guaranteed_pct": round((base * years + signing) / total * 100, 1) if total > 0 else 0,
        },
    }


# ---------------------------------------------------------------------------
# 3. Clause Risk Analysis (LLM call)
# ---------------------------------------------------------------------------

async def analyze_clause_risk(state: "NegotiationState") -> dict[str, Any]:
    """Use LLM to analyze risky clauses in the offer."""
    last_offer = _get_latest_opponent_offer(state)
    if not last_offer:
        return {"risks": [], "risk_level": "none", "summary": "No offer to analyze."}

    term = last_offer.get("term_sheet", {})

    user_side = state.user_side
    if user_side == "player":
        perspective_instruction = (
            "You are the player's legal advisor protecting the player's interests. "
            "Analyze ONLY from the player's perspective — what harms or benefits the player. "
            "A no-trade clause IS a benefit for the player (protects against unwanted transfers). "
            "A zero release clause IS good for the player (harder for clubs to poach). "
            "Flag low base salary, club-favoring option years, short image rights %, "
            "and performance bonuses that inflate risk. "
            "DO NOT analyze club-side risks — only player-side."
        )
    else:
        perspective_instruction = (
            "You are the club's legal advisor. Analyze from the club's perspective — "
            "what constrains the club or drives up cost. "
            "Flag high salary, no-trade clauses that reduce squad flexibility, "
            "high release clauses that lock the player in, and performance bonus obligations."
        )

    prompt = f"""\
{perspective_instruction}

Term Sheet:
{json.dumps(term, indent=2)}

Player Profile:
- Name: {state.player_profile.get('name', 'Unknown')}
- Age: {state.player_profile.get('age', 0)}
- Position: {state.player_profile.get('position', 'Unknown')}

Identify the 3-5 most important risks or concerns for the {'player' if user_side == 'player' else 'club'}.
For each clause, be specific about the EUR amount or % where relevant.

Return JSON with this exact structure (no markdown):
{{
  "risks": [
    {{"clause": "...", "risk_level": "low|medium|high", "explanation": "...", "recommendation": "..."}}
  ],
  "overall_risk_level": "low|medium|high",
  "summary": "One sentence summary"
}}"""

    try:
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
            timeout=30,
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        # Try to parse JSON from the response
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        return result
    except Exception as e:
        logger.warning("Clause risk LLM call failed: %s — using fallback", e)
        return _fallback_clause_risk(term, state)


def _fallback_clause_risk(term: dict, state: "NegotiationState") -> dict[str, Any]:
    """Deterministic fallback for clause risk analysis."""
    risks = []
    age = state.player_profile.get("age", 25)
    years = term.get("contract_years", 1)

    if term.get("no_trade_clause"):
        if state.user_side == "club":
            risks.append({
                "clause": "No-trade clause",
                "risk_level": "high",
                "explanation": "Limits club flexibility to offload player",
                "recommendation": "Negotiate removal or add conditional triggers",
            })
        else:
            risks.append({
                "clause": "No-trade clause",
                "risk_level": "low",
                "explanation": "Protects player from unwanted transfers",
                "recommendation": "Keep — valuable protection",
            })

    if term.get("option_year"):
        if state.user_side == "player":
            risks.append({
                "clause": "Option year",
                "risk_level": "medium",
                "explanation": "Club holds the option, reducing player leverage at end of contract",
                "recommendation": "Request mutual option or player option instead",
            })

    if years >= 4 and age >= 30:
        risks.append({
            "clause": "Contract length",
            "risk_level": "high" if state.user_side == "club" else "low",
            "explanation": f"{years}-year deal for a {age}-year-old — performance decline risk",
            "recommendation": "Reduce to 2-3 years with performance-based extension",
        })

    release = term.get("release_clause_eur", 0)
    base = term.get("base_salary_eur", 0)
    if release > 0 and base > 0:
        ratio = release / base
        if ratio < 3 and state.user_side == "club":
            risks.append({
                "clause": "Release clause",
                "risk_level": "high",
                "explanation": f"Release clause (EUR {release:,}) is only {ratio:.1f}x annual salary — too accessible",
                "recommendation": "Increase to at least 5x annual salary",
            })

    overall = "low"
    if any(r["risk_level"] == "high" for r in risks):
        overall = "high"
    elif any(r["risk_level"] == "medium" for r in risks):
        overall = "medium"

    return {
        "risks": risks,
        "overall_risk_level": overall,
        "summary": f"Found {len(risks)} risk(s), overall risk: {overall}.",
    }


# ---------------------------------------------------------------------------
# 4. Strategy Advice (deterministic — BATNA, ZOPA, action recommendation)
# ---------------------------------------------------------------------------

def compute_strategy_advice(state: "NegotiationState") -> dict[str, Any]:
    """Compute BATNA, walk-away, ZOPA, and recommend action based on round/gap."""
    from agents.strategy_advisor import compute_strategy

    market = state.market_context or {}
    salary_range = market.get("salary_range", {})
    low = salary_range.get("low_eur", 0)
    mid = salary_range.get("mid_eur", 0)
    high = salary_range.get("high_eur", 0)

    strategy = compute_strategy(market, state.club_constraints)

    last_offer = _get_latest_opponent_offer(state)
    last_base = 0
    if last_offer:
        last_base = last_offer.get("term_sheet", {}).get("base_salary_eur", 0)

    # Gap analysis
    gap_to_median = last_base - mid if mid else 0
    gap_pct = round((gap_to_median / mid) * 100, 1) if mid else 0

    # Walk-away: ALWAYS honour the user's explicitly stated threshold first
    user_walk_away = state.walk_away_threshold_eur or 0
    walk_away_source = "your stated minimum"
    if not user_walk_away:
        # Fall back to market-derived threshold if user didn't specify one
        if state.user_side == "player":
            user_walk_away = strategy.get("player_walk_away_salary_eur", int(low * 0.85))
        else:
            user_walk_away = strategy.get("club_walk_away_salary_eur", int(high * 1.15))
        walk_away_source = "market-derived"

    # Should user walk away?
    should_walk = False
    if state.user_side == "player" and last_base > 0:
        should_walk = last_base < user_walk_away and state.current_round >= 3
    elif state.user_side == "club" and last_base > 0:
        should_walk = last_base > user_walk_away and state.current_round >= 3

    # Recommended counter — anchor to mid salary (market median), not below walk-away
    if state.user_side == "player":
        # Counter toward mid or above, always above walk-away
        if last_base < mid:
            recommended_salary = int(mid * 1.05)  # ask 5% above median
        elif last_base < high:
            recommended_salary = int((last_base + high) / 2)
        else:
            recommended_salary = last_base
        # Never recommend below walk-away
        if user_walk_away and recommended_salary < user_walk_away:
            recommended_salary = user_walk_away
    else:
        if last_base > mid:
            recommended_salary = int(mid * 0.95)
        elif last_base > low:
            recommended_salary = int((last_base + low) / 2)
        else:
            recommended_salary = last_base
        if user_walk_away and recommended_salary > user_walk_away:
            recommended_salary = user_walk_away

    # ZOPA display
    zopa = strategy.get("zone_of_possible_agreement", {})
    zopa_low = zopa.get("salary_low_eur", low)
    zopa_high = zopa.get("salary_high_eur", high)

    return {
        "strategy": strategy,
        "gap_to_median_eur": gap_to_median,
        "gap_to_median_pct": gap_pct,
        "user_walk_away_eur": user_walk_away,
        "walk_away_source": walk_away_source,
        "should_walk_away": should_walk,
        "recommended_counter_salary_eur": recommended_salary,
        "rounds_remaining": state.max_rounds - state.current_round,
        "urgency": "high" if state.current_round >= state.max_rounds - 2 else "low",
        "summary": (
            f"{'⚠ WALK AWAY recommended — offer below threshold\n' if should_walk else ''}"
            f"• Gap to median: {gap_pct:+.1f}% (EUR {abs(gap_to_median):,})\n"
            f"• Your walk-away: EUR {user_walk_away:,}/yr ({walk_away_source})\n"
            f"• ZOPA: EUR {zopa_low:,} – EUR {zopa_high:,}/yr\n"
            f"• Counter at: EUR {recommended_salary:,}/yr\n"
            f"• Urgency: {'HIGH ⚡' if state.current_round >= state.max_rounds - 2 else 'Low'} — {state.max_rounds - state.current_round} rounds left"
        ),
    }


# ---------------------------------------------------------------------------
# 5. Fact Check (deterministic — verify term sheet math)
# ---------------------------------------------------------------------------

def fact_check_offer(state: "NegotiationState") -> dict[str, Any]:
    """Verify term sheet math: total = base*years + bonuses."""
    last_offer = _get_latest_opponent_offer(state)
    if not last_offer:
        return {"valid": True, "issues": [], "summary": "No offer to fact-check."}

    term = last_offer.get("term_sheet", {})
    issues = []

    base = term.get("base_salary_eur", 0)
    years = term.get("contract_years", 1)
    signing = term.get("signing_bonus_eur", 0)
    perf = term.get("performance_bonus_eur", 0)

    expected_total = base * years + signing + perf * years
    given_total = term.get("total_value_eur")

    if given_total is not None and abs(given_total - expected_total) > 1:
        issues.append(
            f"Total value mismatch: stated EUR {given_total:,} vs computed EUR {expected_total:,}"
        )

    # Verify percentages are in range
    img = term.get("image_rights_pct", 0)
    if img < 0 or img > 50:
        issues.append(f"Image rights {img}% outside valid range (0-50%)")

    if years < 1 or years > 5:
        issues.append(f"Contract years {years} outside FIFA regulations (1-5)")

    # Check salary is positive
    if base <= 0:
        issues.append("Base salary must be positive")

    # Verify comparables cited in reasoning
    market = state.market_context or {}
    comparables = market.get("comparables", [])
    reasoning = last_offer.get("reasoning", "")
    comp_names = [c.get("name", "").lower() for c in comparables]

    cited_comps = []
    for name in comp_names:
        if name and name in reasoning.lower():
            cited_comps.append(name)

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "computed_total_eur": expected_total,
        "stated_total_eur": given_total,
        "comparables_cited": cited_comps,
        "summary": (
            f"{'✓ PASS — all checks cleared' if not issues else '✗ ISSUES FOUND'}\n"
            f"• Math: {base:,} × {years}yrs + {signing:,} sign + {perf:,}×{years} perf = EUR {expected_total:,}\n"
            + (f"• Stated total: EUR {given_total:,} {'✓ Match' if abs(given_total - expected_total) <= 1 else '✗ Mismatch'}\n" if given_total is not None else "")
            + f"• Contract: {years} yrs {'✓ FIFA compliant' if 1 <= years <= 5 else '✗ Outside 1-5yr range'}\n"
            + f"• Image rights: {img}% {'✓ OK' if 0 <= img <= 50 else '✗ Exceeds 50% cap'}\n"
            + f"• Comparables cited: {', '.join(c.title() for c in cited_comps) if cited_comps else 'None'}"
            + (f"\n• Issues: {'; '.join(issues)}" if issues else "")
        ),
    }


# ---------------------------------------------------------------------------
# Aggregator — recommended action/counter
# ---------------------------------------------------------------------------

def _compute_recommendation(
    state: "NegotiationState",
    offer_analysis: dict,
    strategy_advice: dict,
) -> tuple[str, dict | None, str]:
    """Aggregate sub-agent results into a recommended action + counter."""
    market = state.market_context or {}
    salary_range = market.get("salary_range", {})
    mid = salary_range.get("mid_eur", 0)
    p25 = salary_range.get("low_eur", 0)  # low_eur approximates p25 salary

    last_offer = _get_latest_opponent_offer(state)
    if not last_offer:
        return "COUNTER", None, "No offer to evaluate."

    base = last_offer.get("term_sheet", {}).get("base_salary_eur", 0)
    percentile = offer_analysis.get("market_percentile", 50)

    # Decision logic
    if state.user_side == "player":
        # Player wants high salary
        if base >= mid:
            return "ACCEPT", None, f"Offer meets market median (EUR {mid:,}). Recommend accepting."
        if base < p25 and state.current_round >= 3:
            return "WALK_AWAY", None, f"Offer below p25 (EUR {p25:,}) after {state.current_round} rounds."
    else:
        # Club wants low salary
        if base <= mid:
            return "ACCEPT", None, f"Player demand at or below median (EUR {mid:,}). Recommend accepting."
        if base > salary_range.get("high_eur", mid * 1.4) and state.current_round >= 3:
            return "WALK_AWAY", None, f"Demand above market high after {state.current_round} rounds."

    # Default: COUNTER
    rec_salary = strategy_advice.get("recommended_counter_salary_eur", mid)
    player_name = state.player_profile.get("name", "Unknown")
    position = state.player_profile.get("position", "CM")

    counter_sheet = {
        "player_name": player_name,
        "position": position,
        "base_salary_eur": rec_salary,
        "signing_bonus_eur": int(rec_salary * 0.10),
        "performance_bonus_eur": int(rec_salary * 0.08),
        "contract_years": last_offer.get("term_sheet", {}).get("contract_years", 3),
        "option_year": False,
        "release_clause_eur": 0,
        "image_rights_pct": 10 if state.user_side == "player" else 0,
        "no_trade_clause": state.user_side == "player",
    }

    reasoning = (
        f"Counter at EUR {rec_salary:,}/yr ({percentile}th percentile). "
        f"Gap to median: {offer_analysis.get('vs_median_pct', 0):+.1f}%. "
        f"{strategy_advice.get('rounds_remaining', 0)} rounds remaining."
    )

    return "COUNTER", counter_sheet, reasoning


# ---------------------------------------------------------------------------
# Decision Aggregator — synthesize one paragraph from all 5 agents
# ---------------------------------------------------------------------------

async def _synthesize_war_room_reasoning(
    state: "NegotiationState",
    comparables: dict,
    offer_result: dict,
    clause_risk: dict,
    strategy: dict,
    fact_check: dict,
    recommended_action: str,
    recommended_counter: dict | None,
) -> str:
    """Use LLM to produce one coherent paragraph synthesizing all 5 agents' analyses."""
    try:
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
            timeout=30,
        )

        median_comp = comparables.get("median_comparable_salary_eur", 0)
        median_label = f"EUR {median_comp:,}/yr" if median_comp else "N/A"

        prompt = f"""You are the Decision Aggregator for a football contract negotiation War Room.
Synthesize the analyses from 5 specialist agents into ONE clear paragraph (4-6 sentences) advising what to do next and why.

PLAYER: {state.player_profile.get('name', 'Unknown')} ({state.player_profile.get('position', '?')}, age {state.player_profile.get('age', '?')})
USER SIDE: {state.user_side} (the user is representing the {'player' if state.user_side == 'player' else 'club'})
ROUND: {state.current_round} of {state.max_rounds}
RECOMMENDED ACTION: {recommended_action}
{f"RECOMMENDED COUNTER: EUR {recommended_counter.get('base_salary_eur', 0):,}/yr base salary" if recommended_counter else ""}
MEDIAN COMPARABLE SALARY: {median_label} (use this number when citing comparables — do NOT use any average that may be inflated by outliers)

AGENT ANALYSES:
1. COMPARABLES: {comparables.get('summary', 'N/A')}
2. OFFER ANALYSIS: {offer_result.get('summary', 'N/A')}
3. CLAUSE & RISK: {clause_risk.get('summary', 'N/A')}
4. STRATEGY: {strategy.get('summary', 'N/A')}
5. FACT-CHECK: {fact_check.get('summary', 'N/A')}

Write ONE paragraph that:
- States the recommended action clearly with the specific EUR counter amount
- Cites the MEDIAN comparable salary (not any average) to justify the position
- Mentions the gap between the current offer and market median
- Notes any key clause risk that matters to the {state.user_side}
- Mentions urgency based on rounds remaining
- Sounds like a confident advisor speaking directly to their client

Do NOT use bullet points. Write flowing prose. Keep it under 110 words."""

        result = await llm.ainvoke([HumanMessage(content=prompt)])
        return result.content.strip()
    except Exception as e:
        logger.error("War room synthesis LLM failed: %s", e)
        return _fallback_synthesis(state, comparables, offer_result, strategy, recommended_action, recommended_counter)


def _fallback_synthesis(
    state, comparables, offer_result, strategy, recommended_action, recommended_counter
) -> str:
    """Deterministic fallback if LLM fails."""
    base = 0
    last_offer = _get_latest_opponent_offer(state)
    if last_offer:
        base = last_offer.get("term_sheet", {}).get("base_salary_eur", 0)

    median_comp = comparables.get("median_comparable_salary_eur", 0)
    gap_pct = offer_result.get("vs_median_pct", 0)
    rounds_left = strategy.get("rounds_remaining", 0)
    rec_salary = recommended_counter.get("base_salary_eur", 0) if recommended_counter else 0

    if recommended_action == "ACCEPT":
        return f"The offer of EUR {base:,}/yr meets market standards — comparable players earn a median of EUR {median_comp:,}/yr. We recommend accepting this deal."
    elif recommended_action == "WALK_AWAY":
        return f"After {state.current_round} rounds, the offer of EUR {base:,}/yr remains {abs(gap_pct):.0f}% below market median. This is below your walk-away threshold. We recommend ending negotiations."
    else:
        return (
            f"The current offer of EUR {base:,}/yr is {abs(gap_pct):.0f}% below market median. "
            f"Comparable deals (median EUR {median_comp:,}/yr) support a higher valuation. "
            f"We recommend countering at EUR {rec_salary:,}/yr — this positions us at market rate while leaving room to negotiate. "
            f"With {rounds_left} rounds remaining, there is still time to close the gap."
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_latest_opponent_offer(state: "NegotiationState") -> dict | None:
    """Get the most recent offer from the AI opponent."""
    if not state.rounds:
        return None
    # The opponent side is the opposite of user_side
    opponent_side = "club" if state.user_side == "player" else "player"
    for r in reversed(state.rounds):
        if r.get("side") == opponent_side:
            return r
    return None


# ---------------------------------------------------------------------------
# Main entry point — run all 5 war room agents
# ---------------------------------------------------------------------------

async def run_war_room(state: "NegotiationState") -> dict:
    """Run all 5 war room agents and return their aggregated analysis."""
    # 1-2 and 4-5 are deterministic, 3 is async LLM
    comparables = analyze_comparables(state)
    offer_result = analyze_offer(state)
    strategy = compute_strategy_advice(state)
    fact_check = fact_check_offer(state)

    # LLM call for clause risk
    clause_risk = await analyze_clause_risk(state)

    # Aggregate recommendation
    recommended_action, recommended_counter, reasoning = _compute_recommendation(
        state, offer_result, strategy
    )

    # Synthesize one-paragraph reasoning from all 5 agents
    synthesis = await _synthesize_war_room_reasoning(
        state, comparables, offer_result, clause_risk, strategy, fact_check,
        recommended_action, recommended_counter,
    )

    return {
        "comparables": comparables,
        "offer_analysis": offer_result,
        "clause_risk": clause_risk,
        "strategy": strategy,
        "fact_check": fact_check,
        "recommended_action": recommended_action,
        "recommended_counter": recommended_counter,
        "reasoning": synthesis,
    }
