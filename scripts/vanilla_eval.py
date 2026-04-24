"""
Vanilla baseline: run the same 100 scenarios through ChatGPT via Cloro API.
Each scenario becomes ONE prompt — no multi-agent, no War Room, no iterative rounds.

Usage:
    python scripts/vanilla_eval.py \
        [--concurrency 3] [--dry-run] [--out results/vanilla_raw.csv]

Output: vanilla_raw.csv  (same columns as judged_100runs.csv for direct comparison)
Then run llm_judge.py on it, then analyze_results.py with --vanilla flag.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from scenarios import generate_scenarios

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CLORO_URL = "https://api.cloro.dev/v1/monitor/chatgpt"
CLORO_KEY = os.environ.get("CLORO_API_KEY", "")
RESULTS_DIR  = Path(__file__).parent / "results"
OUTPUT_CSV   = RESULTS_DIR / "vanilla_raw.csv"

CSV_COLUMNS = [
    "run_id", "player_name", "club_name", "budget_eur", "budget_tier",
    "player_position", "player_age", "market_mid_eur", "walk_away_threshold_eur",
    "final_status", "rounds_used", "max_rounds",
    "market_realism", "outcome_quality_club", "outcome_quality_player",
    "efficiency", "compliance_rate",
    "concession_rate_club", "concession_rate_player",
    "concession_rate_club_pct", "concession_rate_player_pct",
    "final_salary_eur",
    "rounds_json",
    "chatgpt_response",
    "error",
]

NEGOTIATION_PROMPT = """\
You are an expert football contract negotiation advisor.

SCENARIO:
- Player: {player_name}, age {player_age}, position {player_position}
- Club: {club_name}
- Club annual salary budget: €{budget_eur:,}
- Player walk-away minimum: €{walk_away_eur:,}/year
- Market salary range: €{market_low:,} (low) / €{market_mid:,} (mid) / €{market_high:,} (high) per year
- Market context: similar players at comparable clubs earn €{market_mid:,}/year median

YOUR TASK:
Negotiate the best possible contract for the player. In a single round, determine:
1. Whether to ACCEPT the club's implied budget offer, COUNTER with a specific number, or WALK AWAY
2. The final recommended base salary (EUR/year)
3. Contract length (1–5 years), signing bonus, performance bonus, release clause, image rights %
4. Your reasoning (2–3 sentences)

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "decision": "ACCEPT" | "COUNTER" | "WALK_AWAY",
  "base_salary_eur": <integer>,
  "contract_years": <integer 1-5>,
  "signing_bonus_eur": <integer>,
  "performance_bonus_eur": <integer>,
  "release_clause_eur": <integer>,
  "image_rights_pct": <integer 0-50>,
  "no_trade_clause": <true|false>,
  "reasoning": "<2-3 sentences>"
}}
"""


def _build_prompt(scenario: dict) -> str:
    return NEGOTIATION_PROMPT.format(
        player_name=scenario["player_name"],
        player_age=scenario["player_age"],
        player_position=scenario["player_position"],
        club_name=scenario["club_name"],
        budget_eur=scenario["budget_eur"],
        walk_away_eur=scenario["walk_away_threshold_eur"],
        market_low=int(scenario["market_mid_eur"] * 0.67),
        market_mid=scenario["market_mid_eur"],
        market_high=int(scenario["market_mid_eur"] * 1.33),
    )


def _extract_json(text: str) -> dict | None:
    """Try to parse JSON from ChatGPT response text."""
    # Try direct parse
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    # Try finding JSON block
    m = re.search(r'\{[\s\S]+\}', text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


def _compute_derived_metrics(parsed: dict | None, scenario: dict) -> dict:
    """Compute paper metrics from the vanilla ChatGPT parsed output."""
    mid = scenario["market_mid_eur"]
    budget = scenario["budget_eur"]
    walk_away = scenario["walk_away_threshold_eur"]
    low = mid * 0.67
    high = mid * 1.33

    if not parsed:
        return {
            "final_status": "ERROR", "rounds_used": 1, "max_rounds": 1,
            "market_realism": 0, "outcome_quality_club": 0, "outcome_quality_player": 0,
            "efficiency": 1.0, "compliance_rate": 0,
            "concession_rate_club": 0, "concession_rate_player": 0,
            "concession_rate_club_pct": 0, "concession_rate_player_pct": 0,
            "final_salary_eur": 0,
        }

    decision = parsed.get("decision", "COUNTER")
    salary   = float(parsed.get("base_salary_eur") or 0)

    # Final status
    status = {"ACCEPT": "ACCEPTED", "WALK_AWAY": "WALKED_AWAY"}.get(decision, "ACCEPTED")

    # Market realism (0-100): how close salary is to market band
    if low <= salary <= high:
        market_realism = 100.0
    elif salary < low:
        dist = low - salary
        market_realism = max(0, 100 * (1 - dist / (low or 1)))
    else:
        dist = salary - high
        market_realism = max(0, 100 * (1 - dist / (high or 1)))

    # Outcome quality club: (budget - salary) / (budget - low)  clamped 0-100
    denom_club = budget - low
    oq_club = max(0, min(100, 100 * (budget - salary) / denom_club)) if denom_club > 0 else 0

    # Outcome quality player: (salary - walk_away) / (high - walk_away) clamped 0-100
    denom_player = high - walk_away
    oq_player = max(0, min(100, 100 * (salary - walk_away) / denom_player)) if denom_player > 0 else 0

    # Vanilla is single-round → efficiency = 1.0 (instant resolution)
    efficiency = 1.0

    # Compliance: budget check + image rights check
    violations = 0
    if salary > budget:
        violations += 1
    if parsed.get("image_rights_pct", 0) > 50:
        violations += 1
    compliance = 1.0 if violations == 0 else 0.5

    # Pseudo-round transcript for judge
    rounds_json = json.dumps([{
        "round_number": 1,
        "side": "player",
        "action": decision,
        "term_sheet": {
            "player_name": scenario["player_name"],
            "position": scenario["player_position"],
            "base_salary_eur": salary,
            "contract_years": parsed.get("contract_years", 4),
            "signing_bonus_eur": parsed.get("signing_bonus_eur", 0),
            "performance_bonus_eur": parsed.get("performance_bonus_eur", 0),
            "release_clause_eur": parsed.get("release_clause_eur", 0),
            "image_rights_pct": parsed.get("image_rights_pct", 0),
            "no_trade_clause": parsed.get("no_trade_clause", False),
        },
        "reasoning": parsed.get("reasoning", ""),
        "constraint_violations": ["salary > budget"] if salary > budget else [],
    }])

    return {
        "final_status": status,
        "rounds_used": 1,
        "max_rounds": 1,
        "market_realism": round(market_realism, 2),
        "outcome_quality_club": round(oq_club, 2),
        "outcome_quality_player": round(oq_player, 2),
        "efficiency": efficiency,
        "compliance_rate": compliance,
        "concession_rate_club": 0,
        "concession_rate_player": 0,
        "concession_rate_club_pct": 0,
        "concession_rate_player_pct": 0,
        "final_salary_eur": salary,
        "rounds_json": rounds_json,
    }


async def run_one(client: httpx.AsyncClient, scenario: dict, semaphore: asyncio.Semaphore) -> dict:
    run_id = str(uuid.uuid4())[:8]
    row: dict = {
        "run_id": run_id,
        **{k: scenario[k] for k in [
            "player_name", "club_name", "budget_eur", "budget_tier",
            "player_position", "player_age", "market_mid_eur", "walk_away_threshold_eur",
        ]},
        "chatgpt_response": "",
        "error": "",
    }

    async with semaphore:
        try:
            prompt = _build_prompt(scenario)
            payload = {
                "prompt":  prompt,
                "country": "US",
                "include": {"markdown": True},
            }
            headers = {
                "Authorization": f"Bearer {CLORO_KEY}",
                "Content-Type":  "application/json",
            }
            resp = await client.post(
                CLORO_URL,
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(connect=10, read=120, write=10, pool=5),
            )
            resp.raise_for_status()
            data = resp.json()

            # Extract response text
            result = data.get("result", {})
            text = (
                result.get("markdown")
                or result.get("text")
                or result.get("html")
                or str(result)
            )
            row["chatgpt_response"] = text[:4000]  # cap for CSV

            parsed = _extract_json(text)
            metrics = _compute_derived_metrics(parsed, scenario)
            row.update(metrics)

        except Exception as e:
            log.error("[%s] failed (%s / %s): %s", run_id, scenario["player_name"], scenario["club_name"], e)
            row["error"] = str(e)
            row.update(_compute_derived_metrics(None, scenario))

    return row


async def run_batch(concurrency: int, dry_run: bool, out_path: Path) -> None:
    scenarios = generate_scenarios()
    if dry_run:
        scenarios = scenarios[:3]
        log.info("DRY RUN: 3 scenarios")

    RESULTS_DIR.mkdir(exist_ok=True)
    semaphore = asyncio.Semaphore(concurrency)

    write_header = not out_path.exists()
    csv_file = out_path.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    if write_header:
        writer.writeheader()
        csv_file.flush()

    completed = 0
    failed    = 0
    start_t   = time.time()

    async def bounded(scenario: dict) -> None:
        nonlocal completed, failed
        row = await run_one(client, scenario, semaphore)
        writer.writerow(row)
        csv_file.flush()
        if row.get("error"):
            failed += 1
        else:
            completed += 1
        log.info(
            "[%3d/%d] %-22s  status=%-12s  salary=%s  err=%s",
            completed + failed, len(scenarios),
            scenario["player_name"][:22],
            row.get("final_status", "?"),
            row.get("final_salary_eur", "?"),
            str(row.get("error", ""))[:60],
        )

    limits = httpx.Limits(max_connections=concurrency + 2, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits) as client:
        await asyncio.gather(*[bounded(s) for s in scenarios])

    csv_file.close()
    log.info("Done. %d ok / %d failed in %.1fs → %s",
             completed, failed, time.time() - start_t, out_path)

    if dry_run:
        import pandas as pd
        df = pd.read_csv(out_path)
        print("\n--- DRY RUN RESULT ---")
        for _, r in df.iterrows():
            print(f"\n{r['player_name']} / {r['club_name']}")
            print(f"  status={r['final_status']}  salary={r['final_salary_eur']}")
            print(f"  chatgpt_response[:300]={str(r['chatgpt_response'])[:300]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--out",         default=str(OUTPUT_CSV))
    args = parser.parse_args()
    asyncio.run(run_batch(args.concurrency, args.dry_run, Path(args.out)))


if __name__ == "__main__":
    main()
