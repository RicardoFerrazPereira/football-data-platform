import json
from pathlib import Path
from collections import Counter

RAW_PATH = Path("data/raw/lineups")

orphan_ids = [
    15235403,
    15235405,
    15235408,
    15235410,
    15235429,
    15237963,
    15237985,
]

for match_id in orphan_ids:
    file = RAW_PATH / f"{match_id}.json"

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\nPartida: {match_id}")

    for side in ["home", "away"]:
        side_data = data.get(side) or {}
        players = (
            (side_data.get("players") or [])
            + (side_data.get("substitutes") or [])
        )

        team_ids = Counter(
            player.get("teamId")
            for player in players
            if player.get("teamId") is not None
        )

        names = [
            player.get("player", {}).get("name")
            for player in players[:3]
        ]

        print(
            f"{side.upper()}: "
            f"team_ids={dict(team_ids)}, "
            f"jogadores_exemplo={names}"
        )