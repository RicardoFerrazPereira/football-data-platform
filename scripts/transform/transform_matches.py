import logging
import json
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

MATCHES_PATH = Path("data/raw/matches/matches.json")

PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

# =====================================
# LOAD
# =====================================

if not MATCHES_PATH.exists():
    raise SystemExit(
        f"Arquivo não encontrado: {MATCHES_PATH}\n"
        "Execute primeiro: python collect_matches.py"
    )

logger.info(f"Lendo: {MATCHES_PATH}")

with open(MATCHES_PATH, "r", encoding="utf-8") as f:
    matches = json.load(f)

logger.info(f"Registros carregados: {len(matches)}")

# =====================================
# DATAFRAME
# =====================================

df = pd.DataFrame(matches)

logger.info(f"Total linhas antes deduplicação: {len(df)}")

# =====================================
# REMOVE DUPLICATES
# =====================================

df = df.drop_duplicates(subset=["match_id"])

logger.info(f"Total linhas após deduplicação: {len(df)}")

# =====================================
# DATE CONVERSION
# =====================================

df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce", utc=True)
df["match_date"] = df["match_date"].dt.tz_localize(None)  # remove timezone p/ Parquet

# =====================================
# SORT
# =====================================

df = df.sort_values("match_date").reset_index(drop=True)

# =====================================
# SAVE PARQUET
# =====================================

output_file = PROCESSED_PATH / "matches.parquet"

df.to_parquet(output_file, engine="pyarrow", index=False)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Arquivo salvo em: {output_file}")
logger.info(f"Total matches: {len(df)}")
logger.info(
    f"Período: {df['match_date'].min().date()} → {df['match_date'].max().date()}"
)
logger.info(f"\nSchema:\n{df.dtypes}")
