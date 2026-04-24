"""Generate 100 evaluation scenarios: 20 players × 5 budget tiers."""

from __future__ import annotations

import json
import pathlib

BUDGET_TIERS = [
    ("tight",     0.70, 0.55),
    ("low",       0.85, 0.65),
    ("market",    1.00, 0.70),
    ("high",      1.20, 0.75),
    ("generous",  1.50, 0.80),
]

CLUBS = [
    "Arsenal", "Manchester City", "Real Madrid", "Barcelona", "PSG",
    "Bayern Munich", "Juventus", "Chelsea", "Liverpool", "Borussia Dortmund",
]

PLAYER_PRIORITIES = ["high_salary", "image_rights", "no_trade_clause"]
CLUB_PRIORITIES   = ["low_cost", "performance_bonus"]


def generate_scenarios() -> list[dict]:
    data_path = pathlib.Path(__file__).parent.parent / "backend" / "data" / "sample_players.json"
    players = json.loads(data_path.read_text())["players"]

    scenarios: list[dict] = []
    club_idx = 0

    for player in players:
        mid = float(player["market_context"]["salary_range"]["mid_eur"])
        current_club = player.get("current_club", "")

        for tier_name, budget_mult, walkaway_mult in BUDGET_TIERS:
            # pick a club that isn't the player's own
            club = CLUBS[club_idx % len(CLUBS)]
            if club == current_club:
                club_idx += 1
                club = CLUBS[club_idx % len(CLUBS)]
            club_idx += 1

            scenarios.append({
                # API request fields
                "player_name":             player["name"],
                "club_name":               club,
                "budget_eur":              int(mid * budget_mult),
                "walk_away_threshold_eur": int(mid * walkaway_mult),
                "max_years":               4,
                "user_side":               "player",
                "player_priorities":       PLAYER_PRIORITIES,
                "priorities":              CLUB_PRIORITIES,
                # metadata (not sent to API, kept for CSV)
                "budget_tier":             tier_name,
                "market_mid_eur":          int(mid),
                "player_position":         player.get("position", ""),
                "player_age":              player.get("age", 0),
            })

    return scenarios  # exactly 100


if __name__ == "__main__":
    s = generate_scenarios()
    print(f"Generated {len(s)} scenarios")
    for row in s[:3]:
        print(row)
