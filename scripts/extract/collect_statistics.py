import json
import logging
import sys
import time
from pathlib import Path

import cloudscraper
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

BASE_URL = "https://api.sofascore.com/api/v1"

# Filtro de ano — ajuste ou remova quando quiser expandir pra todos os anos
FILTER_YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026

MATCHES_PATH = Path("data/processed/matches.parquet")

SAVE_PATH = Path("data/raw/statistics")
SAVE_PATH.mkdir(parents=True, exist_ok=True)

SLEEP_BETWEEN_REQUESTS = 1  # segundos entre requisições
MAX_RETRIES = 3             # tentativas por partida

# =====================================
# LOAD MATCHES
# =====================================

if not MATCHES_PATH.exists():
    raise SystemExit(
        f"Arquivo não encontrado: {MATCHES_PATH}\n"
        "Execute primeiro: python transform_matches.py"
    )

df_matches = pd.read_parquet(MATCHES_PATH)

logger.info(f"Matches carregados: {len(df_matches)}")

# =====================================
# FILTER BY YEAR
# =====================================

df_matches = df_matches[df_matches["match_date"].dt.year == FILTER_YEAR]

logger.info(f"Matches filtrados ({FILTER_YEAR}): {len(df_matches)}")

# =====================================
# SCRAPER
# =====================================

scraper = cloudscraper.create_scraper()

# =====================================
# HELPERS
# =====================================

def fetch_with_retry(url: str, max_retries: int = MAX_RETRIES) -> dict | None:
    """Faz a requisição com retry e backoff exponencial."""
    for attempt in range(max_retries):
        try:
            response = scraper.get(url)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                logger.warning("404 — estatísticas não encontradas na API")
                return None

            logger.warning(
                f"STATUS {response.status_code} — "
                f"tentativa {attempt + 1}/{max_retries}"
            )

        except Exception as e:
            logger.warning(f"Exceção na tentativa {attempt + 1}/{max_retries}: {e}")

        time.sleep(2 ** attempt)  # backoff: 1s, 2s, 4s

    logger.error(f"Falha após {max_retries} tentativas: {url}")
    return None

# =====================================
# LOOP
# =====================================

total = len(df_matches)

for i, (_, row) in enumerate(df_matches.iterrows(), start=1):

    match_id = row["match_id"]

    logger.info(f"[{i}/{total}] Match ID: {match_id}")

    # =====================================
    # SKIP EXISTING
    # =====================================

    output_file = SAVE_PATH / f"{match_id}.json"

    if output_file.exists():
        logger.info("Arquivo já existe — pulando")
        continue

    # =====================================
    # REQUEST
    # =====================================

    url = f"{BASE_URL}/event/{match_id}/statistics"

    data = fetch_with_retry(url)

    if data is None:
        logger.warning(f"Sem dados para match_id {match_id} — pulando")
        continue

    # =====================================
    # SAVE RAW
    # =====================================

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    logger.info(f"Salvo: {output_file.name}")

    # =====================================
    # RATE LIMIT
    # =====================================

    time.sleep(SLEEP_BETWEEN_REQUESTS)

# =====================================
# LOG FINAL
# =====================================

logger.info("COLETA DE ESTATÍSTICAS FINALIZADA")