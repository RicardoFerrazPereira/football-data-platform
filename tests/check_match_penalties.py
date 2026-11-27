from pathlib import Path

import pandas as pd


MATCHES_PATH = Path("data/processed/matches.parquet")


matches = pd.read_parquet(MATCHES_PATH)

penalty_matches = matches[
    matches["home_score_penalties"].notna()
    | matches["away_score_penalties"].notna()
].copy()

print("\n================================")
print("MATCHES WITH PENALTIES")
print("================================")

print(f"Total de partidas com pênaltis: {len(penalty_matches)}")

if penalty_matches.empty:
    print("\nNenhuma partida com campos de pênaltis preenchidos.")
else:
    columns = [
        "match_id",
        "match_date",
        "tournament_name",
        "season_name",
        "home_team_name",
        "away_team_name",
        "home_score",
        "away_score",
        "home_score_penalties",
        "away_score_penalties",
        "home_score_current",
        "away_score_current",
        "status",
    ]

    print("\nPartidas encontradas:")
    print(
        penalty_matches[columns]
        .sort_values("match_date")
        .to_string(index=False)
    )

print("\n================================")
print("Vasco matches with penalties")
print("================================")

vasco_penalty_matches = penalty_matches[
    (penalty_matches["home_team_id"] == 1974)
    | (penalty_matches["away_team_id"] == 1974)
].copy()

print(
    f"Partidas do Vasco com pênaltis: "
    f"{len(vasco_penalty_matches)}"
)

if not vasco_penalty_matches.empty:
    print(
        vasco_penalty_matches[columns]
        .sort_values("match_date")
        .to_string(index=False)
    )