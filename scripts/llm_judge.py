"""
LLM-as-judge: score completed negotiations on a 6-dimension rubric.

Usage:
    python scripts/llm_judge.py \
        --input  results/auto_negotiate_100runs.csv \
        --output results/judged_100runs.csv \
        [--model gpt-4o] [--concurrency 3]

Reads each row, calls GPT-4o with a structured rubric prompt, appends
judge_* score columns to the output CSV. Runs are processed incrementally
so the script can be safely restarted after a crash.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
from openai import AsyncOpenAI

# Load API key from backend .env if not already in environment
def _load_env() -> None:
    if os.environ.get("OPENAI_API_KEY"):
        return
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JUDGE_COLUMNS = [
    "judge_market_alignment",
    "judge_player_outcome",
    "judge_club_outcome",
    "judge_contract_structure",
    "judge_reasoning_quality",
    "judge_overall",
    "judge_justifications",
]

RUBRIC_SYSTEM = """\
You are an expert football contract analyst evaluating AI-driven contract negotiations.
Score the negotiation on 6 dimensions using integers 0-10 (10 = excellent).
Be objective and consistent. Base scores strictly on the data provided.

RUBRIC:
- market_alignment (0-10): Is the final salary within the market p25-p75 band? 10=dead center, 5=at band edge, 0=far outside.
- player_outcome (0-10): Does the deal serve the player's interests relative to their walk-away threshold and p75 target?
- club_outcome (0-10): Does the deal represent good value for the club relative to their budget?
- contract_structure (0-10): Are bonuses, image rights, release clause, and contract length well-balanced and reasonable?
- reasoning_quality (0-10): Were the negotiating agents' round-by-round reasoning chains logical, strategic, and coherent?
- overall (0-10): Holistic assessment — would this be a fair, viable, real-world football contract?

Respond in valid JSON only:
{
  "judge_market_alignment": <int>,
  "judge_player_outcome": <int>,
  "judge_club_outcome": <int>,
  "judge_contract_structure": <int>,
  "judge_reasoning_quality": <int>,
  "judge_overall": <int>,
  "judge_justifications": {
    "market_alignment": "<one sentence>",
    "player_outcome": "<one sentence>",
    "club_outcome": "<one sentence>",
    "contract_structure": "<one sentence>",
    "reasoning_quality": "<one sentence>",
    "overall": "<one sentence>"
  }
}"""


def _build_prompt(row: dict) -> str:
    rounds = []
    try:
        rounds = json.loads(row.get("rounds_json", "[]"))
    except Exception:
        pass

    transcript_lines = []
    for r in rounds:
        ts = r.get("term_sheet") or {}
        transcript_lines.append(
            f"  Round {r.get('round_number','')} [{r.get('side','')}] {r.get('action','')} | "
            f"base_salary=€{ts.get('base_salary_eur') or '?'} years={ts.get('contract_years','?')} | "
            f"reasoning: {str(r.get('reasoning',''))[:120]}"
        )

    transcript = "\n".join(transcript_lines) if transcript_lines else "  (no rounds recorded)"

    return f"""\
PLAYER: {row.get('player_name')} | Position: {row.get('player_position')} | Age: {row.get('player_age')}
CLUB: {row.get('club_name')} | Budget: €{int(row.get('budget_eur',0)):,}/yr
MARKET: mid=€{int(row.get('market_mid_eur',0)):,}  |  walk-away threshold: €{int(row.get('walk_away_threshold_eur',0)):,}

OUTCOME: {row.get('final_status')}  |  Rounds used: {row.get('rounds_used')}  |  Final salary: €{row.get('final_salary_eur','?')}
Market realism score (computed): {row.get('market_realism','?')}
Compliance rate: {row.get('compliance_rate','?')}

ROUND-BY-ROUND TRANSCRIPT:
{transcript}
"""


async def judge_row(
    client: AsyncOpenAI,
    row: dict,
    model: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        prompt = _build_prompt(row)
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": RUBRIC_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.0,
                max_tokens=600,
                response_format={"type": "json_object"},
            )
            scores = json.loads(resp.choices[0].message.content)
            return {
                "judge_market_alignment":   scores.get("judge_market_alignment"),
                "judge_player_outcome":     scores.get("judge_player_outcome"),
                "judge_club_outcome":       scores.get("judge_club_outcome"),
                "judge_contract_structure": scores.get("judge_contract_structure"),
                "judge_reasoning_quality":  scores.get("judge_reasoning_quality"),
                "judge_overall":            scores.get("judge_overall"),
                "judge_justifications":     json.dumps(scores.get("judge_justifications", {})),
            }
        except Exception as e:
            log.warning("Judge failed for run_id=%s: %s", row.get("run_id"), e)
            return {c: None for c in JUDGE_COLUMNS}


async def run_judge(input_path: Path, output_path: Path, model: str, concurrency: int) -> None:
    df = pd.read_csv(input_path)
    log.info("Loaded %d rows from %s", len(df), input_path)

    # Skip already-judged rows if output exists
    already_done: set[str] = set()
    if output_path.exists():
        existing = pd.read_csv(output_path)
        already_done = set(existing["run_id"].astype(str))
        log.info("Skipping %d already-judged rows", len(already_done))

    pending = df[~df["run_id"].astype(str).isin(already_done)]
    if pending.empty:
        log.info("All rows already judged.")
        return

    api_key = os.environ.get("OPENAI_API_KEY", "")
    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(concurrency)

    write_header = not output_path.exists()
    out_file = output_path.open("a", newline="", encoding="utf-8")
    out_cols = list(df.columns) + JUDGE_COLUMNS
    import csv
    writer = csv.DictWriter(out_file, fieldnames=out_cols, extrasaction="ignore")
    if write_header:
        writer.writeheader()
        out_file.flush()

    completed = 0

    async def process(row_dict: dict) -> None:
        nonlocal completed
        scores = await judge_row(client, row_dict, model, semaphore)
        merged = {**row_dict, **scores}
        writer.writerow(merged)
        out_file.flush()
        completed += 1
        log.info("[%d/%d] %s → overall=%s", completed, len(pending), row_dict.get("player_name"), scores.get("judge_overall"))

    tasks = [process(row.to_dict()) for _, row in pending.iterrows()]
    await asyncio.gather(*tasks)

    out_file.close()
    log.info("Judge complete. %d rows written to %s", completed, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-as-judge rubric scorer for negotiation results")
    parser.add_argument("--input",       required=True,          help="Input CSV (from batch_eval.py)")
    parser.add_argument("--output",      required=True,          help="Output CSV with judge scores appended")
    parser.add_argument("--model",       default="gpt-4o",       help="OpenAI model to use as judge")
    parser.add_argument("--concurrency", type=int, default=3,    help="Max concurrent judge calls")
    args = parser.parse_args()

    asyncio.run(run_judge(
        Path(args.input),
        Path(args.output),
        args.model,
        args.concurrency,
    ))


if __name__ == "__main__":
    main()
