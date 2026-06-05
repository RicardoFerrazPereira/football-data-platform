import logging
from pathlib import Path

import pandas as pd

# =====================================
# LOGGING
# =====================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# =====================================
# CONFIG
# =====================================

PROCESSED_PATH = Path("data/processed")

MATCHES_PATH = PROCESSED_PATH / "matches.parquet"

# =====================================
# LOAD MATCHES
# =====================================

if not MATCHES_PATH.exists():
    raise SystemExit(
        f"Arquivo não encontrado: {MATCHES_PATH}\n"
        "Execute primeiro: python transform_matches.py"
    )

matches = pd.read_parquet(MATCHES_PATH)

logger.info(f"Matches carregados: {len(matches)}")

# =====================================
# HOME TEAMS
# =====================================

home_teams = matches[["home_team_id", "home_team_name"]].copy()
home_teams.columns = ["team_id", "team_name"]

# =====================================
# AWAY TEAMS
# =====================================

away_teams = matches[["away_team_id", "away_team_name"]].copy()
away_teams.columns = ["team_id", "team_name"]

# =====================================
# CONCAT
# =====================================

teams = pd.concat([home_teams, away_teams], ignore_index=True)

logger.info(f"Total linhas antes deduplicação: {len(teams)}")

# =====================================
# REMOVE NULLS
# =====================================

teams = teams.dropna(subset=["team_id", "team_name"])

# =====================================
# TYPES
# =====================================

teams["team_id"] = teams["team_id"].astype("int64")
teams["team_name"] = teams["team_name"].astype("string")

# =====================================
# REMOVE DUPLICATES
# =====================================

teams = teams.drop_duplicates(subset=["team_id"])

logger.info(f"Total teams após deduplicação: {len(teams)}")

# =====================================
# SORT + RESET INDEX
# =====================================

teams = teams.sort_values("team_name").reset_index(drop=True)

# =====================================
# SAVE
# =====================================

output_file = PROCESSED_PATH / "teams.parquet"

teams.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Arquivo salvo em: {output_file}")
logger.info(f"Total teams: {len(teams)}")
logger.info(f"\nSchema:\n{teams.dtypes}")
logger.info(f"\nAmostra:\n{teams.head(10).to_string()}")
