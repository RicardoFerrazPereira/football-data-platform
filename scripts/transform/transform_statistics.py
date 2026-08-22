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

RAW_PATH = Path("data/raw/statistics")
PROCESSED_PATH = Path("data/processed")

PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

SIDES = ["home", "away"]

# =====================================
# VALIDATE INPUT
# =====================================

json_files = list(RAW_PATH.glob("*.json"))

if not json_files:
    raise SystemExit(
        f"Nenhum arquivo encontrado em: {RAW_PATH}\n"
        "Execute primeiro: python collect_statistics.py"
    )

logger.info(f"Arquivos encontrados: {len(json_files)}")

# =====================================
# HELPERS
# =====================================

def parse_numeric_value(value) -> float | None:
    """Converte valores de estatísticas para numérico quando possível."""
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip().replace("%", "").replace(",", "")
        if value == "":
            return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# =====================================
# STORAGE
# =====================================

statistics_data = []

# =====================================
# LOOP FILES
# =====================================

for file in json_files:

    match_id = int(file.stem)

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for period in data.get("statistics", []):

        period_name = period.get("period")

        for group in period.get("groups", []):

            group_name = group.get("groupName")

            for item in group.get("statisticsItems", []):

                statistic_name = item.get("name")

                for side in SIDES:

                    value = item.get(side)

                    statistics_data.append({
                        "match_id": match_id,
                        "period": period_name,
                        "group_name": group_name,
                        "statistic_name": statistic_name,
                        "team_side": side,
                        "value": value,
                        "value_numeric": parse_numeric_value(value),
                    })

# =====================================
# DATAFRAME
# =====================================

df = pd.DataFrame(statistics_data)

logger.info(f"Total linhas antes deduplicação: {len(df)}")

# =====================================
# REMOVE DUPLICATES
# =====================================

df = df.drop_duplicates()

logger.info(f"Total linhas após deduplicação: {len(df)}")

# =====================================
# SORT + RESET INDEX
# =====================================

df = df.sort_values(
    ["match_id", "period", "group_name", "statistic_name", "team_side"]
).reset_index(drop=True)

# =====================================
# OPTIMIZE DTYPES
# =====================================

df["match_id"] = df["match_id"].astype("int64")
df["team_side"] = df["team_side"].astype("category")
df["period"] = df["period"].astype("category")
df["group_name"] = df["group_name"].astype("category")

# =====================================
# SAVE PARQUET
# =====================================

output_file = PROCESSED_PATH / "statistics.parquet"

df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Arquivo salvo em: {output_file}")
logger.info(f"Total registros: {len(df)}")
logger.info(f"\nSchema:\n{df.dtypes}")
logger.info(f"\nAmostra:\n{df.head(10).to_string()}")