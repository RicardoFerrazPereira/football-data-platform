
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
player_statistics = pd.read_parquet(
    PROCESSED_PATH / "player_statistics.parquet"
)
statistics = pd.read_parquet(PROCESSED_PATH / "statistics.parquet")

print("Datasets carregados com sucesso.")

# =====================================
# VALIDATION HELPERS
# =====================================

errors = []


def section(title):
    print("\n")
    print("=" * 40)
    print(title)
    print("=" * 40)


def check_zero(description, count):
    count = int(count)

    if count == 0:
        print(f"[OK] {description}: {count}")
    else:
        print(f"[ERROR] {description}: {count}")
        errors.append(description)


def check_info(description, value):
    print(f"[INFO] {description}: {value}")


# =====================================
# MATCHES VALIDATION
# =====================================

section("MATCHES VALIDATION")

check_zero(
    "Duplicated match_id",
    matches["match_id"].duplicated().sum()
)

check_zero("Null match_id", matches["match_id"].isnull().sum())
check_zero("Null home_team_id", matches["home_team_id"].isnull().sum())
check_zero("Null away_team_id", matches["away_team_id"].isnull().sum())
check_zero("Null season_id", matches["season_id"].isnull().sum())
check_zero("Null tournament_id", matches["tournament_id"].isnull().sum())

# =====================================
# TEAMS VALIDATION
# =====================================

section("TEAMS VALIDATION")

check_zero(
    "Duplicated team_id",
    teams["team_id"].duplicated().sum()
)

check_zero("Null team_id", teams["team_id"].isnull().sum())
check_zero("Null team_name", teams["team_name"].isnull().sum())

# =====================================
# PLAYERS VALIDATION
# =====================================

section("PLAYERS VALIDATION")

check_zero(
    "Duplicated player_id",
    players["player_id"].duplicated().sum()
)

check_zero("Null player_id", players["player_id"].isnull().sum())
check_zero("Null player_name", players["player_name"].isnull().sum())

# Position can legitimately be null.
check_info(
    "Null position (informational)",
    players["position"].isnull().sum()
)

# =====================================
# LINEUPS VALIDATION
# =====================================

section("LINEUPS VALIDATION")

check_zero("Null match_id", lineups["match_id"].isnull().sum())
check_zero("Null team_id", lineups["team_id"].isnull().sum())
check_zero("Null player_id", lineups["player_id"].isnull().sum())

# =====================================
# DUPLICATED PLAYER IN MATCH
# =====================================

duplicated_lineups = lineups.duplicated(
    subset=["match_id", "team_id", "player_id"]
).sum()

check_zero("Duplicated player in same match", duplicated_lineups)

# =====================================
# PLAYER STATISTICS VALIDATION
# =====================================

section("PLAYER STATISTICS VALIDATION")

check_zero(
    "Null match_id",
    player_statistics["match_id"].isnull().sum()
)

check_zero(
    "Null team_id",
    player_statistics["team_id"].isnull().sum()
)

check_zero(
    "Null player_id",
    player_statistics["player_id"].isnull().sum()
)

check_zero(
    "Null player_name",
    player_statistics["player_name"].isnull().sum()
)

check_zero(
    "Null statistic_name",
    player_statistics["statistic_name"].isnull().sum()
)

check_zero(
    "Null value",
    player_statistics["value"].isnull().sum()
)

# =====================================
# DUPLICATED PLAYER STATISTICS
# =====================================

duplicated_stats = player_statistics.duplicated(
    subset=["match_id", "team_id", "player_id", "statistic_name"]
).sum()

check_zero("Duplicated player statistics", duplicated_stats)

# =====================================
# STATISTICS VALIDATION
# =====================================

section("STATISTICS VALIDATION")

check_zero("Null match_id", statistics["match_id"].isnull().sum())
check_zero("Null period", statistics["period"].isnull().sum())
check_zero("Null group_name", statistics["group_name"].isnull().sum())
check_zero(
    "Null statistic_key",
    statistics["statistic_key"].isnull().sum()
)
check_zero("Null team_side", statistics["team_side"].isnull().sum())
check_zero("Null value", statistics["value"].isnull().sum())

duplicated_statistics = statistics.duplicated(
    subset=[
        "match_id",
        "period",
        "group_name",
        "statistic_key",
        "team_side"
    ]
).sum()

check_zero("Duplicated match statistics", duplicated_statistics)

# =====================================
# INVALID METRICS
# =====================================

section("INVALID METRICS")

# accuratePass must not exceed totalPass.

accurate_pass = player_statistics[
    player_statistics["statistic_name"] == "accuratePass"
][
    ["match_id", "team_id", "player_id", "value_numeric"]
].rename(
    columns={"value_numeric": "accurate_pass"}
)

total_pass = player_statistics[
    player_statistics["statistic_name"] == "totalPass"
][
    ["match_id", "team_id", "player_id", "value_numeric"]
].rename(
    columns={"value_numeric": "total_pass"}
)

pass_validation = accurate_pass.merge(
    total_pass,
    on=["match_id", "team_id", "player_id"],
    how="inner"
)

invalid_pass = pass_validation[
    pass_validation["accurate_pass"] > pass_validation["total_pass"]
]

check_zero("accuratePass > totalPass", len(invalid_pass))

# =====================================
# RELATIONSHIP VALIDATION
# =====================================

section("RELATIONSHIP VALIDATION")

# =====================================
# PLAYER EXISTS
# =====================================

invalid_players = ~player_statistics["player_id"].isin(
    players["player_id"]
)

check_zero(
    "player_statistics with invalid player_id",
    invalid_players.sum()
)

invalid_lineup_players = ~lineups["player_id"].isin(
    players["player_id"]
)

check_zero(
    "lineups with invalid player_id",
    invalid_lineup_players.sum()
)

# =====================================
# MATCH EXISTS
# =====================================

invalid_lineup_matches = ~lineups["match_id"].isin(
    matches["match_id"]
)

check_zero(
    "lineups with invalid match_id",
    invalid_lineup_matches.sum()
)

invalid_player_stats_matches = ~player_statistics["match_id"].isin(
    matches["match_id"]
)

check_zero(
    "player_statistics with invalid match_id",
    invalid_player_stats_matches.sum()
)

invalid_statistics_matches = ~statistics["match_id"].isin(
    matches["match_id"]
)

check_zero(
    "statistics with invalid match_id",
    invalid_statistics_matches.sum()
)

# =====================================
# TEAM EXISTS
# =====================================

invalid_teams_home = ~matches["home_team_id"].isin(teams["team_id"])
invalid_teams_away = ~matches["away_team_id"].isin(teams["team_id"])

check_zero("Invalid home_team_id", invalid_teams_home.sum())
check_zero("Invalid away_team_id", invalid_teams_away.sum())

invalid_lineup_teams = ~lineups["team_id"].isin(teams["team_id"])

check_zero(
    "lineups with invalid team_id",
    invalid_lineup_teams.sum()
)

invalid_player_stats_teams = ~player_statistics["team_id"].isin(
    teams["team_id"]
)

check_zero(
    "player_statistics with invalid team_id",
    invalid_player_stats_teams.sum()
)

# =====================================
# TEAM BELONGS TO MATCH
# =====================================

match_teams = pd.concat(
    [
        matches[["match_id", "home_team_id"]].rename(
            columns={"home_team_id": "team_id"}
        ),
        matches[["match_id", "away_team_id"]].rename(
            columns={"away_team_id": "team_id"}
        )
    ],
    ignore_index=True
).drop_duplicates()

lineup_team_check = lineups[
    ["match_id", "team_id"]
].merge(
    match_teams,
    on=["match_id", "team_id"],
    how="left",
    indicator=True
)

invalid_lineup_match_teams = (
    lineup_team_check["_merge"] != "both"
).sum()

check_zero(
    "lineups with team_id outside the match",
    invalid_lineup_match_teams
)

player_stats_team_check = player_statistics[
    ["match_id", "team_id"]
].drop_duplicates().merge(
    match_teams,
    on=["match_id", "team_id"],
    how="left",
    indicator=True
)

invalid_player_stats_match_teams = (
    player_stats_team_check["_merge"] != "both"
).sum()

check_zero(
    "player_statistics with team_id outside the match",
    invalid_player_stats_match_teams
)

# =====================================
# SUMMARY
# =====================================

section("SUMMARY")

print(f"Matches: {len(matches):,}")
print(f"Teams: {len(teams):,}")
print(f"Players: {len(players):,}")
print(f"Lineups: {len(lineups):,}")
print(f"Player Statistics: {len(player_statistics):,}")
print(f"Statistics: {len(statistics):,}")

print("\n================================")

if errors:
    print("VALIDATION FAILED")
    print(f"Total errors: {len(errors)}")

    for error in errors:
        print(f"- {error}")

    print("================================")
    raise SystemExit(1)

print("ALL VALIDATIONS PASSED")
print("================================")
