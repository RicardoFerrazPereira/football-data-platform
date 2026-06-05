import json
import logging
import sys
import time
from datetime import datetime, timezone
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

TEAM_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1974

SEASONS_PATH = Path("data/raw/seasons/seasons.json")

RAW_PATH = Path("data/raw/matches/raw")
SAVE_PATH = Path("data/raw/matches")

RAW_PATH.mkdir(parents=True, exist_ok=True)
SAVE_PATH.mkdir(parents=True, exist_ok=True)

SLEEP_BETWEEN_PAGES = 1  # segundos entre páginas
SLEEP_BETWEEN_SEASONS = 1  # segundos entre seasons
MAX_RETRIES = 3  # tentativas por página

logger.info(f"Coletando partidas — TEAM_ID referência: {TEAM_ID}")

# =====================================
# LOAD SEASONS
# =====================================

if not SEASONS_PATH.exists():
    raise SystemExit(
        f"Arquivo de seasons não encontrado: {SEASONS_PATH}\n"
        f"Execute primeiro: python collect_seasons.py {TEAM_ID}"
    )

with open(SEASONS_PATH, "r", encoding="utf-8") as f:
    seasons = json.load(f)

logger.info(f"Seasons carregadas: {len(seasons)}")

# =====================================
# SCRAPER
# =====================================

scraper = cloudscraper.create_scraper()

# =====================================
# HELPERS
# =====================================


def parse_date(timestamp: int | None) -> str | None:
    """Converte Unix timestamp para data legível (YYYY-MM-DD)."""
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")


def fetch_with_retry(url: str, max_retries: int = MAX_RETRIES) -> dict | None:
    """Faz a requisição com retry e backoff exponencial."""
    for attempt in range(max_retries):
        try:
            response = scraper.get(url)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                logger.warning("404 — season sem eventos disponíveis")
                return None

            logger.warning(
                f"STATUS {response.status_code} — "
                f"tentativa {attempt + 1}/{max_retries}"
            )

        except Exception as e:
            logger.warning(f"Exceção na tentativa {attempt + 1}/{max_retries}: {e}")

        time.sleep(2**attempt)  # backoff: 1s, 2s, 4s

    logger.error(f"Falha após {max_retries} tentativas: {url}")
    return None


def normalize_event(
    event: dict,
    tournament_id: int,
    tournament_name: str,
    season_id: int,
    season_name: str,
) -> dict:
    """Normaliza um evento da API para o formato padrão."""
    home_team = event.get("homeTeam", {})
    away_team = event.get("awayTeam", {})
    home_score = event.get("homeScore", {})
    away_score = event.get("awayScore", {})
    status_data = event.get("status", {})

    return {
        "match_id": event.get("id"),
        "tournament_id": tournament_id,
        "tournament_name": tournament_name,
        "season_id": season_id,
        "season_name": season_name,
        "home_team_id": home_team.get("id"),
        "home_team_name": home_team.get("name"),
        "away_team_id": away_team.get("id"),
        "away_team_name": away_team.get("name"),
        "home_score": home_score.get("current"),
        "away_score": away_score.get("current"),
        "match_date": parse_date(event.get("startTimestamp")),
        "status": status_data.get("type"),
        "slug": event.get("slug"),
    }


# =====================================
# STORAGE
# =====================================

all_matches = []

# =====================================
# LOOP SEASONS
# =====================================

for season in seasons:

    tournament_id = season["tournament_id"]
    season_id = season["season_id"]
    tournament_name = season["tournament_name"]
    season_name = season["season_name"]

    logger.info(f"Processando: {tournament_name} | {season_name}")

    page = 0

    while True:

        url = (
            f"{BASE_URL}/unique-tournament/{tournament_id}"
            f"/season/{season_id}/events/last/{page}"
        )

        data = fetch_with_retry(url)

        if data is None:
            break

        events = data.get("events", [])

        if not events:
            logger.info("Sem mais eventos nesta season")
            break

        logger.info(f"PAGE {page} | Eventos encontrados: {len(events)}")

        # =====================================
        # SAVE RAW PAGE
        # =====================================

        raw_file = RAW_PATH / f"{tournament_id}_{season_id}_page_{page}.json"

        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # =====================================
        # NORMALIZATION
        # =====================================

        for event in events:
            match = normalize_event(
                event, tournament_id, tournament_name, season_id, season_name
            )
            all_matches.append(match)

        # =====================================
        # PAGINATION
        # =====================================

        if not data.get("hasNextPage", False):
            break

        page += 1
        time.sleep(SLEEP_BETWEEN_PAGES)

    time.sleep(SLEEP_BETWEEN_SEASONS)

# =====================================
# REMOVE DUPLICATES
# =====================================

clean_matches = list({m["match_id"]: m for m in all_matches}.values())

# =====================================
# SAVE CLEAN
# =====================================

matches_file = SAVE_PATH / "matches.json"

with open(matches_file, "w", encoding="utf-8") as f:
    json.dump(clean_matches, f, ensure_ascii=False, indent=4)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Arquivo salvo em: {matches_file}")
logger.info(f"TOTAL MATCHES: {len(clean_matches)}")
