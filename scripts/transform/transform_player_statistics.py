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

statistics_data = []

# =====================================
# LOOP FILES
# =====================================

for file in json_files:

    try:

        match_id = int(file.stem)

        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for side in SIDES:

            side_data = data.get(side, {})

            if not side_data:
                continue

            for group in PLAYER_GROUPS:

                for item in side_data.get(group, []):

                    player = item.get("player", {})
                    player_id = player.get("id")
                    team_id = item.get("teamId")

                    if player_id is None or team_id is None:
                        continue

                    statistics = item.get("statistics", {})

                    if not statistics:
                        continue

                    for stat_name, stat_value in statistics.items():

                        # Ignora valores aninhados
                        if isinstance(stat_value, dict):
                            continue

                        statistics_data.append({
                            "match_id": match_id,
                            "team_id": team_id,
                            "player_id": player_id,
                            "player_name": player.get("name"),
                            "side": side,
                            "position": item.get("position"),
                            "substitute": item.get("substitute", False),
                            "statistic_name": stat_name,
                            "value": stat_value,
                        })

    except Exception as e:
        logger.error(f"Erro ao processar {file.name}: {e}")

# =====================================
# DATAFRAME
# =====================================

df = pd.DataFrame(statistics_data)

if df.empty:
    raise SystemExit("Nenhuma estatística encontrada. Verifique os arquivos de entrada.")

logger.info(f"Total linhas antes deduplicação: {len(df)}")

# =====================================
# REMOVE DUPLICATES
# =====================================

df = df.drop_duplicates()

logger.info(f"Total linhas após deduplicação: {len(df)}")

# =====================================
# REMOVE NULLS
# =====================================

df = df.dropna(subset=["match_id", "team_id", "player_id"])

# =====================================
# VALUE NUMERIC
# =====================================

df["value_numeric"] = pd.to_numeric(df["value"], errors="coerce")

# =====================================
# SORT + RESET INDEX
# =====================================

df = df.sort_values(
    ["match_id", "team_id", "player_id", "statistic_name"]
).reset_index(drop=True)

# =====================================
# TYPES
# =====================================

df["match_id"] = df["match_id"].astype("int64")
df["team_id"] = df["team_id"].astype("int64")
df["player_id"] = df["player_id"].astype("int64")
df["statistic_name"] = df["statistic_name"].astype("category")
df["side"] = df["side"].astype("category")
df["position"] = df["position"].astype("category")
df["substitute"] = df["substitute"].astype("bool")

# =====================================
# SAVE
# =====================================

output_file = PROCESSED_PATH / "player_statistics.parquet"

df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Arquivo salvo em: {output_file}")
logger.info(f"Total registros: {len(df)}")
logger.info(f"\nNull check:\n{df.isnull().sum()}")
logger.info(f"\nMétricas disponíveis:\n{sorted(df['statistic_name'].unique())}")
logger.info(f"\nSchema:\n{df.dtypes}")
logger.info(f"\nAmostra:\n{df.head(10).to_string()}")