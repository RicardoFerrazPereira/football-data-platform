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

PLAYER_GROUPS = ["players", "substitutes"]
SIDES = ["home", "away"]

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

players = []

# =====================================
# LOOP FILES
# =====================================

for file in json_files:

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for side in SIDES:

        side_data = data.get(side, {})

        if not side_data:
            continue

        for group in PLAYER_GROUPS:

            for item in side_data.get(group, []):

                player = item.get("player", {})

                if not player:
                    continue

                country = player.get("country", {})

                players.append({
                    "player_id": player.get("id"),
                    "player_name": player.get("name"),
                    "short_name": player.get("shortName"),
                    "slug": player.get("slug"),
                    "position": player.get("position"),
                    "jersey_number": item.get("jerseyNumber"),
                    "height": player.get("height"),
                    "preferred_foot": player.get("preferredFoot"),
                    "country_name": country.get("name"),
                    "country_alpha2": country.get("alpha2"),
                    "birth_timestamp": player.get("dateOfBirthTimestamp"),
                })

# =====================================
# DATAFRAME
# =====================================

df = pd.DataFrame(players)

logger.info(f"Total linhas antes deduplicação: {len(df)}")

# =====================================
# REMOVE DUPLICATES
# =====================================

df = df.drop_duplicates(subset=["player_id"])

logger.info(f"Total linhas após deduplicação: {len(df)}")

# =====================================
# DATE CONVERSION
# =====================================

df["birth_date"] = pd.to_datetime(
    df["birth_timestamp"], unit="s", errors="coerce", utc=True
).dt.tz_localize(None)

df = df.drop(columns=["birth_timestamp"])

# =====================================
# SORT + RESET INDEX
# =====================================

df = df.sort_values("player_name").reset_index(drop=True)

# =====================================
# SAVE PARQUET
# =====================================

output_file = PROCESSED_PATH / "players.parquet"

df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Arquivo salvo em: {output_file}")
logger.info(f"Total players: {len(df)}")
logger.info(f"\nSchema:\n{df.dtypes}")
logger.info(f"\nAmostra:\n{df.head(10).to_string()}")