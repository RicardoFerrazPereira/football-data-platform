import json
import logging
import sys
import time
from pathlib import Path

import cloudscraper

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

# Aceita TEAM_ID via argumento ou usa Vasco como padrão
TEAM_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1974

TOURNAMENTS_PATH = Path(f"data/raw/tournaments/team_{TEAM_ID}_tournaments.json")

RAW_PATH = Path("data/raw/seasons/raw")
SAVE_PATH = Path("data/raw/seasons")

RAW_PATH.mkdir(parents=True, exist_ok=True)
SAVE_PATH.mkdir(parents=True, exist_ok=True)

SLEEP_BETWEEN_REQUESTS = 1  # segundos entre requisições

logger.info(f"Coletando seasons para TEAM_ID: {TEAM_ID}")

# =====================================
# LOAD TOURNAMENTS
# =====================================

if not TOURNAMENTS_PATH.exists():
    raise SystemExit(
        f"Arquivo de torneios não encontrado: {TOURNAMENTS_PATH}\n"
        f"Execute primeiro: python collect_tournaments.py {TEAM_ID}"
    )

with open(TOURNAMENTS_PATH, "r", encoding="utf-8") as f:
    tournaments = json.load(f)

logger.info(f"Torneios carregados: {len(tournaments)}")

# =====================================
# SCRAPER
# =====================================

scraper = cloudscraper.create_scraper()

# =====================================
# COLLECT SEASONS
# =====================================

all_seasons = []

for tournament in tournaments:

    tournament_id = tournament["tournament_id"]
    tournament_name = tournament["tournament_name"]

    logger.info(f"Coletando seasons: {tournament_name} (ID: {tournament_id})")

    url = f"{BASE_URL}/unique-tournament/{tournament_id}/seasons"

    response = scraper.get(url)

    logger.info(f"STATUS: {response.status_code}")

    if response.status_code != 200:
        logger.warning(f"Erro ao coletar seasons de '{tournament_name}' — pulando")
        continue

    data = response.json()

    # =====================================
    # SAVE RAW POR TORNEIO
    # =====================================

    raw_file = RAW_PATH / f"tournament_{tournament_id}_seasons_raw.json"

    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # =====================================
    # NORMALIZATION
    # =====================================

    seasons = data.get("seasons", [])

    logger.info(f"Seasons encontradas: {len(seasons)}")

    for season in seasons:
        all_seasons.append(
            {
                "season_id": season.get("id"),
                "season_name": season.get("name"),
                "year": season.get("year"),
                "tournament_id": tournament_id,
                "tournament_name": tournament_name,
            }
        )

    time.sleep(SLEEP_BETWEEN_REQUESTS)

# =====================================
# REMOVE DUPLICATES
# =====================================

clean_seasons = list({s["season_id"]: s for s in all_seasons}.values())

# =====================================
# SAVE CLEAN
# =====================================

save_file = SAVE_PATH / "seasons.json"

with open(save_file, "w", encoding="utf-8") as f:
    json.dump(clean_seasons, f, ensure_ascii=False, indent=4)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Seasons salvas em: {save_file}")
logger.info(f"TOTAL SEASONS: {len(clean_seasons)}")
