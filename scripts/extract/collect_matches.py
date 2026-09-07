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

SLEEP_BETWEEN_PAGES = 1
SLEEP_BETWEEN_SEASONS = 1

MAX_RETRIES = 3


logger.info(
    f"Coletando partidas — TEAM_ID referência: {TEAM_ID}"
)


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


logger.info(
    f"Seasons carregadas: {len(seasons)}"
)


# =====================================
# LOAD EXISTING MATCHES
# INCREMENTAL CONTROL
# =====================================

matches_file = SAVE_PATH / "matches.json"


if matches_file.exists():

    with open(matches_file, "r", encoding="utf-8") as f:

        existing_matches = {
            m["match_id"]: m
            for m in json.load(f)
        }

    logger.info(
        f"Partidas já existentes carregadas: "
        f"{len(existing_matches)}"
    )

else:

    existing_matches = {}

    logger.info(
        "Nenhuma partida existente — "
        "iniciando coleta do zero"
    )


# =====================================
# SCRAPER
# =====================================

scraper = cloudscraper.create_scraper()


# =====================================
# HELPERS
# =====================================

def parse_date(timestamp: int | None) -> str | None:
    """
    Converte Unix timestamp para data.
    """

    if not timestamp:
        return None

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc
    ).strftime("%Y-%m-%d")


def fetch_with_retry(
    url: str,
    max_retries: int = MAX_RETRIES
) -> dict | None:
    """
    Faz requisição com retry
    e backoff exponencial.
    """

    for attempt in range(max_retries):

        try:

            response = scraper.get(url)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:

                logger.warning(
                    "404 — season sem eventos disponíveis"
                )

                return None

            logger.warning(
                f"STATUS {response.status_code} — "
                f"tentativa {attempt + 1}/{max_retries}"
            )

        except Exception as e:

            logger.warning(
                f"Exceção na tentativa "
                f"{attempt + 1}/{max_retries}: {e}"
            )

        time.sleep(2 ** attempt)

    logger.error(
        f"Falha após {max_retries} tentativas: {url}"
    )

    return None


# =====================================
# NORMALIZE EVENT
# =====================================

def normalize_event(
    event: dict,
    tournament_id: int,
    tournament_name: str,
    season_id: int,
    season_name: str,
) -> dict:
    """
    Normaliza um evento da API
    para o formato padrão do projeto.
    """

    home_team = event.get("homeTeam", {})
    away_team = event.get("awayTeam", {})

    home_score = event.get("homeScore", {})
    away_score = event.get("awayScore", {})

    status_data = event.get("status", {})

    return {

        # =====================================
        # MATCH
        # =====================================

        "match_id": event.get("id"),

        "match_date": parse_date(
            event.get("startTimestamp")
        ),

        "status": status_data.get("type"),

        "slug": event.get("slug"),


        # =====================================
        # TOURNAMENT
        # =====================================

        "tournament_id": tournament_id,

        "tournament_name": tournament_name,

        "season_id": season_id,

        "season_name": season_name,


        # =====================================
        # HOME TEAM
        # =====================================

        "home_team_id": home_team.get("id"),

        "home_team_name": home_team.get("name"),


        # =====================================
        # AWAY TEAM
        # =====================================

        "away_team_id": away_team.get("id"),

        "away_team_name": away_team.get("name"),


        # =====================================
        # SCORE - NORMAL TIME
        # =====================================

        "home_score": home_score.get(
            "normaltime",
            home_score.get("display")
        ),

        "away_score": away_score.get(
            "normaltime",
            away_score.get("display")
        ),


        # =====================================
        # SCORE - FIRST HALF
        # =====================================

        "home_score_period1": home_score.get(
            "period1"
        ),

        "away_score_period1": away_score.get(
            "period1"
        ),


        # =====================================
        # SCORE - SECOND HALF
        # =====================================

        "home_score_period2": home_score.get(
            "period2"
        ),

        "away_score_period2": away_score.get(
            "period2"
        ),


        # =====================================
        # SCORE - PENALTIES
        # =====================================

        "home_score_penalties": home_score.get(
            "penalties"
        ),

        "away_score_penalties": away_score.get(
            "penalties"
        ),


        # =====================================
        # SCORE - SOFASCORE CURRENT
        # =====================================

        "home_score_current": home_score.get(
            "current"
        ),

        "away_score_current": away_score.get(
            "current"
        ),
    }


# =====================================
# STORAGE
# =====================================

new_matches = {}


# =====================================
# LOOP SEASONS
# =====================================

for season in seasons:

    tournament_id = season["tournament_id"]
    season_id = season["season_id"]

    tournament_name = season["tournament_name"]
    season_name = season["season_name"]

    logger.info(
        f"Processando: "
        f"{tournament_name} | "
        f"{season_name}"
    )

    page = 0

    season_has_new = False


    # =====================================
    # PAGINATION
    # =====================================

    while True:

        url = (
            f"{BASE_URL}/unique-tournament/"
            f"{tournament_id}"
            f"/season/{season_id}"
            f"/events/last/{page}"
        )

        data = fetch_with_retry(url)

        if data is None:
            break

        events = data.get(
            "events",
            []
        )

        if not events:

            logger.info(
                "Sem mais eventos nesta season"
            )

            break


        # =====================================
        # INCREMENTAL CHECK
        # =====================================

        new_in_page = [
            event
            for event in events
            if event.get("id") not in existing_matches
        ]


        logger.info(
            f"PAGE {page} | "
            f"Total: {len(events)} | "
            f"Novos: {len(new_in_page)}"
        )


        if not new_in_page:

            logger.info(
                "Página sem novidades — "
                "encerrando season"
            )

            break


        season_has_new = True


        # =====================================
        # SAVE RAW PAGE
        # =====================================

        raw_file = (
            RAW_PATH
            / f"{tournament_id}_{season_id}_page_{page}.json"
        )


        with open(
            raw_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )


        # =====================================
        # NORMALIZATION
        # =====================================

        for event in new_in_page:

            match = normalize_event(
                event,
                tournament_id,
                tournament_name,
                season_id,
                season_name,
            )

            new_matches[
                match["match_id"]
            ] = match


        # =====================================
        # PAGINATION
        # =====================================

        if not data.get(
            "hasNextPage",
            False
        ):
            break


        page += 1

        time.sleep(
            SLEEP_BETWEEN_PAGES
        )


    if not season_has_new:

        logger.info(
            "Season sem novas partidas — "
            "pulando"
        )


    time.sleep(
        SLEEP_BETWEEN_SEASONS
    )


# =====================================
# MERGE EXISTING + NEW
# =====================================

all_matches = {
    **existing_matches,
    **new_matches,
}


clean_matches = list(
    all_matches.values()
)


logger.info(
    f"Partidas existentes: "
    f"{len(existing_matches)}"
)

logger.info(
    f"Partidas novas: "
    f"{len(new_matches)}"
)

logger.info(
    f"Total final: "
    f"{len(clean_matches)}"
)


# =====================================
# SAVE CLEAN
# =====================================

with open(
    matches_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        clean_matches,
        f,
        ensure_ascii=False,
        indent=4
    )


# =====================================
# LOG FINAL
# =====================================

logger.info(
    f"Arquivo salvo em: {matches_file}"
)