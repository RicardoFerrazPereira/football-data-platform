from pathlib import Path

import pandas as pd

# =====================================
# CONFIG
# =====================================

PROCESSED_PATH = Path("data/processed")

# =====================================
# LOAD DATASETS
# =====================================

print("\n================================")
print("LOADING DATASETS")
print("================================")

matches = pd.read_parquet(PROCESSED_PATH / "matches.parquet")

teams = pd.read_parquet(PROCESSED_PATH / "teams.parquet")

players = pd.read_parquet(PROCESSED_PATH / "players.parquet")

lineups = pd.read_parquet(PROCESSED_PATH / "lineups.parquet")

player_statistics = pd.read_parquet(PROCESSED_PATH / "player_statistics.parquet")

statistics = pd.read_parquet(PROCESSED_PATH / "statistics.parquet")

print("Datasets carregados com sucesso.")

# =====================================
# HELPERS
# =====================================


def section(title):

    print("\n")
    print("=" * 40)
    print(title)
    print("=" * 40)


# =====================================
# MATCHES VALIDATION
# =====================================

section("MATCHES VALIDATION")

print("Duplicated match_id:", matches["match_id"].duplicated().sum())

print("Null match_id:", matches["match_id"].isnull().sum())

print("Null home_team_id:", matches["home_team_id"].isnull().sum())

print("Null away_team_id:", matches["away_team_id"].isnull().sum())

print("Null season_id:", matches["season_id"].isnull().sum())

print("Null tournament_id:", matches["tournament_id"].isnull().sum())

# =====================================
# TEAMS VALIDATION
# =====================================

section("TEAMS VALIDATION")

print("Duplicated team_id:", teams["team_id"].duplicated().sum())

print("Null team_id:", teams["team_id"].isnull().sum())

print("Null team_name:", teams["team_name"].isnull().sum())

# =====================================
# PLAYERS VALIDATION
# =====================================

section("PLAYERS VALIDATION")

print("Duplicated player_id:", players["player_id"].duplicated().sum())

print("Null player_id:", players["player_id"].isnull().sum())

print("Null player_name:", players["player_name"].isnull().sum())

print("Null position:", players["position"].isnull().sum())

# =====================================
# LINEUPS VALIDATION
# =====================================

section("LINEUPS VALIDATION")

print("Null match_id:", lineups["match_id"].isnull().sum())

print("Null team_id:", lineups["team_id"].isnull().sum())

print("Null player_id:", lineups["player_id"].isnull().sum())

# =====================================
# DUPLICATED PLAYER IN MATCH
# =====================================

duplicated_lineups = lineups.duplicated(
    subset=["match_id", "team_id", "player_id"]
).sum()

print("Duplicated player in same match:", duplicated_lineups)

# =====================================
# PLAYER STATISTICS VALIDATION
# =====================================

section("PLAYER STATISTICS VALIDATION")

print("Null match_id:", player_statistics["match_id"].isnull().sum())

print("Null team_id:", player_statistics["team_id"].isnull().sum())

print("Null player_id:", player_statistics["player_id"].isnull().sum())

print("Null statistic_name:", player_statistics["statistic_name"].isnull().sum())

# =====================================
# DUPLICATED STATS
# =====================================

duplicated_stats = player_statistics.duplicated(
    subset=["match_id", "team_id", "player_id", "statistic_name"]
).sum()

print("Duplicated player statistics:", duplicated_stats)

# =====================================
# INVALID METRICS
# =====================================

section("INVALID METRICS")

# accuratePass > totalPass

accurate_pass = player_statistics[
    player_statistics["statistic_name"] == "accuratePass"
][["match_id", "player_id", "value_numeric"]].rename(
    columns={"value_numeric": "accurate_pass"}
)

total_pass = player_statistics[player_statistics["statistic_name"] == "totalPass"][
    ["match_id", "player_id", "value_numeric"]
].rename(columns={"value_numeric": "total_pass"})

pass_validation = accurate_pass.merge(
    total_pass, on=["match_id", "player_id"], how="inner"
)

invalid_pass = pass_validation[
    pass_validation["accurate_pass"] > pass_validation["total_pass"]
]

print("accuratePass > totalPass:", len(invalid_pass))

# =====================================
# RELATIONSHIP VALIDATION
# =====================================

section("RELATIONSHIP VALIDATION")

# =====================================
# PLAYER EXISTS
# =====================================

invalid_players = ~player_statistics["player_id"].isin(players["player_id"])

print("player_statistics " "with invalid player_id:", invalid_players.sum())

# =====================================
# MATCH EXISTS
# =====================================

invalid_matches = ~lineups["match_id"].isin(matches["match_id"])

print("lineups with invalid match_id:", invalid_matches.sum())

# =====================================
# TEAM EXISTS
# =====================================

invalid_teams_home = ~matches["home_team_id"].isin(teams["team_id"])

invalid_teams_away = ~matches["away_team_id"].isin(teams["team_id"])

print("Invalid home_team_id:", invalid_teams_home.sum())

print("Invalid away_team_id:", invalid_teams_away.sum())

# =====================================
# SUMMARY
# =====================================

section("SUMMARY")

print(f"Matches: {len(matches):,}")

print(f"Teams: {len(teams):,}")

print(f"Players: {len(players):,}")

print(f"Lineups: {len(lineups):,}")

print(f"Player Statistics: " f"{len(player_statistics):,}")

print(f"Statistics: {len(statistics):,}")

print("\n================================")
print("VALIDATION FINISHED")
print("================================")
