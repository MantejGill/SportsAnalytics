"""
Batch evaluation runner: 100 automated negotiations.

Usage:
    python scripts/batch_eval.py [--base-url URL] [--concurrency N] [--dry-run]

The script connects to a running Auto-Negotiate backend, runs each scenario
autonomously (auto-decision follows War Room recommendation), and writes
results incrementally to scripts/results/auto_negotiate_100runs.csv.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import sys
import time
import uuid
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).parent))
from scenarios import generate_scenarios

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"
OUTPUT_CSV  = RESULTS_DIR / "auto_negotiate_100runs.csv"

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
    "error",
]

API_REQUEST_FIELDS = {
    "player_name", "club_name", "budget_eur", "walk_away_threshold_eur",
    "max_years", "user_side", "player_priorities", "priorities",
}

POLL_INTERVAL  = 4    # seconds between state polls
MAX_ITERATIONS = 120  # safety cap (~8 min per negotiation)


# ---------------------------------------------------------------------------
# Per-negotiation runner (polling-based, no SSE parsing)
# ---------------------------------------------------------------------------

async def run_one(client: httpx.AsyncClient, scenario: dict, base_url: str) -> dict:
    run_id = str(uuid.uuid4())[:8]
    row: dict = {
        "run_id": run_id,
        **{k: scenario[k] for k in [
            "player_name", "club_name", "budget_eur", "budget_tier",
            "player_position", "player_age", "market_mid_eur", "walk_away_threshold_eur",
        ]},
        "error": "",
    }

    try:
        # 1. Start negotiation
        request_body = {k: v for k, v in scenario.items() if k in API_REQUEST_FIELDS}
        resp = await client.post(f"{base_url}/api/negotiate", json=request_body, timeout=30)
        resp.raise_for_status()
        rid = resp.json()["request_id"]
        log.debug("[%s] started negotiation %s", run_id, rid)

        decided_count = 0  # how many war_room decisions we've acted on
        final_status_from_events = ""

        for iteration in range(MAX_ITERATIONS):
            await asyncio.sleep(POLL_INTERVAL)

            # Poll full negotiation state
            try:
                sr = await client.get(f"{base_url}/api/negotiation/{rid}", timeout=15)
                sr.raise_for_status()
            except Exception as poll_err:
                log.warning("[%s] poll error iter %d: %s", run_id, iteration, poll_err)
                continue

            data   = sr.json()
            status = data.get("status", "")
            events = data.get("events", [])

            # Count war_room_complete events from the server
            war_room_events = [e for e in events if e.get("type") == "war_room_complete"]

            if status == "awaiting_user" and len(war_room_events) > decided_count:
                # New decision required
                wr_data = war_room_events[-1].get("data", war_room_events[-1])
                action  = wr_data.get("recommended_action", "COUNTER")
                counter = wr_data.get("recommended_counter")

                # Fallback if counter missing: nudge last opponent offer +5%
                if action == "COUNTER" and not counter:
                    opp_events = [e for e in events if e.get("type") == "opponent_offer"]
                    if opp_events:
                        last_ts = opp_events[-1].get("data", {}).get("term_sheet", {})
                        if last_ts:
                            counter = dict(last_ts)
                            counter["base_salary_eur"] = int(counter.get("base_salary_eur", 0) * 1.05)

                decide_body = {
                    "action":     action,
                    "term_sheet": counter,
                    "reasoning":  "Auto-eval: following War Room recommendation",
                }
                try:
                    dr = await client.post(
                        f"{base_url}/api/decide/{rid}",
                        json=decide_body,
                        timeout=15,
                    )
                    dr.raise_for_status()
                    decided_count += 1
                    log.debug("[%s] round %d → %s", run_id, decided_count, action)
                except Exception as de:
                    log.warning("[%s] decide failed: %s", run_id, de)

            elif status == "completed":
                # Grab final negotiation-level status from state
                ns = data.get("state", {})
                final_status_from_events = ns.get("status", "")
                log.debug("[%s] negotiation completed after %d iters (ns_status=%s)",
                          run_id, iteration, final_status_from_events)
                break

            elif status == "error":
                raise RuntimeError(data.get("error") or "negotiation error")

        # If loop exhausted without "completed", wait up to 60s more
        if not final_status_from_events:
            for _ in range(15):
                await asyncio.sleep(4)
                try:
                    sr = await client.get(f"{base_url}/api/negotiation/{rid}", timeout=15)
                    d = sr.json()
                    if d.get("status") == "completed":
                        final_status_from_events = d.get("state", {}).get("status", "")
                        break
                except Exception:
                    pass

        # 2. Fetch metrics
        metrics: dict = {}
        rounds_json = "[]"
        try:
            mr = await client.get(f"{base_url}/api/metrics/{rid}", timeout=15)
            mr.raise_for_status()
            metrics = mr.json().get("metrics", {})

            fr = await client.get(f"{base_url}/api/negotiation/{rid}", timeout=15)
            if fr.status_code == 200:
                state_dict = fr.json().get("state", {})
                rounds_json = json.dumps(state_dict.get("rounds", []))
        except Exception as me:
            log.warning("[%s] metrics fetch failed: %s", run_id, me)

        # Determine final status: prefer metrics, then event state, then round fallback
        ns_status = metrics.get("final_status", "")
        if not ns_status or ns_status == "NEGOTIATING":
            ns_status = final_status_from_events
        if not ns_status or ns_status == "NEGOTIATING":
            try:
                rounds = json.loads(rounds_json)
                if rounds:
                    last_action = rounds[-1].get("action", "")
                    rounds_used = int(metrics.get("rounds_used") or len(rounds))
                    max_rounds  = int(metrics.get("max_rounds") or 8)
                    if last_action == "ACCEPT":
                        ns_status = "ACCEPTED"
                    elif last_action == "WALK_AWAY":
                        ns_status = "WALKED_AWAY"
                    else:
                        ns_status = "MAX_ROUNDS" if rounds_used >= max_rounds else "NEGOTIATING"
            except Exception:
                pass

        row.update({
            "final_status":               ns_status,
            "rounds_used":                metrics.get("rounds_used", ""),
            "max_rounds":                 metrics.get("max_rounds", ""),
            "market_realism":             metrics.get("market_realism", ""),
            "outcome_quality_club":       metrics.get("outcome_quality_club", ""),
            "outcome_quality_player":     metrics.get("outcome_quality_player", ""),
            "efficiency":                 metrics.get("efficiency", ""),
            "compliance_rate":            metrics.get("compliance_rate", ""),
            "concession_rate_club":       metrics.get("concession_rate_club", ""),
            "concession_rate_player":     metrics.get("concession_rate_player", ""),
            "concession_rate_club_pct":   metrics.get("concession_rate_club_pct", ""),
            "concession_rate_player_pct": metrics.get("concession_rate_player_pct", ""),
            "final_salary_eur":           metrics.get("final_salary_eur", ""),
            "rounds_json":                rounds_json,
        })

    except Exception as e:
        log.error("[%s] run_one failed (%s / %s): %s",
                  run_id, scenario["player_name"], scenario["club_name"], e)
        row["error"] = str(e)

    return row


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

async def run_batch(base_url: str, concurrency: int, dry_run: bool) -> None:
    scenarios = generate_scenarios()
    if dry_run:
        scenarios = scenarios[:1]
        log.info("DRY RUN: 1 scenario")

    RESULTS_DIR.mkdir(exist_ok=True)
    semaphore = asyncio.Semaphore(concurrency)

    write_header = not OUTPUT_CSV.exists()
    csv_file = OUTPUT_CSV.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    if write_header:
        writer.writeheader()
        csv_file.flush()

    completed = 0
    failed    = 0
    start_t   = time.time()

    async def bounded_run(scenario: dict) -> None:
        nonlocal completed, failed
        async with semaphore:
            row = await run_one(client, scenario, base_url)
            writer.writerow(row)
            csv_file.flush()
            if row.get("error"):
                failed += 1
            else:
                completed += 1
            pct     = (completed + failed) / len(scenarios) * 100
            elapsed = time.time() - start_t
            log.info(
                "[%3d/%d  %4.1f%%  %5.0fs] %-22s  status=%-12s  salary=%s  err=%s",
                completed + failed, len(scenarios), pct, elapsed,
                scenario["player_name"][:22],
                row.get("final_status", "?"),
                row.get("final_salary_eur", "?"),
                str(row.get("error", ""))[:60],
            )

    limits = httpx.Limits(max_connections=concurrency + 4,
                          max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits) as client:
        await asyncio.gather(*[bounded_run(s) for s in scenarios])

    csv_file.close()
    log.info("Done. %d ok / %d failed in %.1fs → %s",
             completed, failed, time.time() - start_t, OUTPUT_CSV)

    if dry_run:
        print("\n--- DRY RUN RESULT ---")
        import pandas as pd
        df = pd.read_csv(OUTPUT_CSV)
        print(df.to_string())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url",    default="http://localhost:8100")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--out",         default=None, help="Override output CSV path")
    args = parser.parse_args()
    if args.out:
        global OUTPUT_CSV
        OUTPUT_CSV = Path(args.out)
    asyncio.run(run_batch(args.base_url, args.concurrency, args.dry_run))


if __name__ == "__main__":
    main()
