import json
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

RAW_PATH = Path("data/raw/lineups")
PROCESSED_PATH = Path("data/processed")

PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

SIDES = ["home", "away"]
PLAYER_GROUPS = ["players", "substitutes"]

# =====================================
# VALIDATE INPUT
# =====================================

json_files = list(RAW_PATH.glob("*.json"))

if not json_files:
    raise SystemExit(
        f"Nenhum arquivo encontrado em: {RAW_PATH}\n"
        "Execute primeiro: python collect_lineups.py"
    )

logger.info(f"Arquivos encontrados: {len(json_files)}")

# =====================================
# STORAGE
# =====================================

lineups = []

# =====================================
# LOOP FILES
# =====================================

for file in json_files:

    match_id = int(file.stem)

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for side in SIDES:

        side_data = data.get(side, {})

        if not side_data:
            continue

        formation = side_data.get("formation")

        for group in PLAYER_GROUPS:

            for item in side_data.get(group, []):

                player = item.get("player", {})

                if not player:
                    continue

                team_id = item.get("teamId")
                player_id = player.get("id")

                if team_id is None or player_id is None:
                    continue

                substitute = item.get("substitute", False)

                lineups.append({
                    "match_id": match_id,
                    "team_id": team_id,
                    "player_id": player_id,
                    "player_name": player.get("name"),
                    "starter": not substitute,
                    "substitute": substitute,
                    "position": item.get("position"),
                    "shirt_number": item.get("jerseyNumber"),
                    "captain": item.get("captain", False),
                    "formation": formation,
                    "side": side,
                })

# =====================================
# DATAFRAME
# =====================================

df = pd.DataFrame(lineups)

logger.info(f"Total linhas antes deduplicação: {len(df)}")

# =====================================
# EMPTY CHECK
# =====================================

if df.empty:
    raise SystemExit("Nenhum lineup encontrado. Verifique os arquivos de entrada.")

# =====================================
# REMOVE NULLS
# =====================================

df = df.dropna(subset=["match_id", "team_id", "player_id"])

# =====================================
# REMOVE DUPLICATES
# =====================================

df = df.drop_duplicates(subset=["match_id", "team_id", "player_id"])

logger.info(f"Total linhas após deduplicação: {len(df)}")

# =====================================
# TYPES
# =====================================

df["match_id"] = df["match_id"].astype("int64")
df["team_id"] = df["team_id"].astype("int64")
df["player_id"] = df["player_id"].astype("int64")
df["starter"] = df["starter"].astype("bool")
df["substitute"] = df["substitute"].astype("bool")
df["side"] = df["side"].astype("category")
df["position"] = df["position"].astype("category")

# =====================================
# SORT + RESET INDEX
# =====================================

df = df.sort_values(
    ["match_id", "team_id", "starter"],
    ascending=[True, True, False]
).reset_index(drop=True)

# =====================================
# SAVE PARQUET
# =====================================

output_file = PROCESSED_PATH / "lineups.parquet"

df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Arquivo salvo em: {output_file}")
logger.info(f"Total registros: {len(df)}")
logger.info(f"\nSchema:\n{df.dtypes}")
logger.info(f"\nAmostra:\n{df.head(10).to_string()}")