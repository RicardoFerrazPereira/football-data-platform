import json
import logging
import sys
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

RAW_PATH = Path("data/raw/tournaments")
RAW_PATH.mkdir(parents=True, exist_ok=True)

logger.info(f"Coletando torneios para TEAM_ID: {TEAM_ID}")

# =====================================
# REQUEST
# =====================================

url = f"{BASE_URL}/team/{TEAM_ID}/unique-tournaments"

scraper = cloudscraper.create_scraper()

response = scraper.get(url)

logger.info(f"STATUS CODE: {response.status_code}")

# =====================================
# VALIDATION
# =====================================

if response.status_code != 200:
    raise SystemExit(
        f"Erro na requisição — STATUS {response.status_code}: {response.text}"
    )

# =====================================
# JSON
# =====================================

data = response.json()

# =====================================
# SAVE RAW
# =====================================

raw_file = RAW_PATH / f"team_{TEAM_ID}_tournaments_raw.json"

with open(raw_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

logger.info(f"RAW salvo em: {raw_file}")

# =====================================
# NORMALIZATION
# =====================================

unique_tournaments = data.get("uniqueTournaments", [])

tournaments = [
    {
        "tournament_id": tournament.get("id"),
        "tournament_name": tournament.get("name"),
        "tournament_slug": tournament.get("slug"),
        "category": tournament.get("category", {}).get("name"),
        "category_slug": tournament.get("category", {}).get("slug"),
    }
    for tournament in unique_tournaments
]

# =====================================
# REMOVE DUPLICATES
# =====================================

clean_tournaments = list({t["tournament_id"]: t for t in tournaments}.values())

# =====================================
# SAVE CLEAN
# =====================================

clean_file = RAW_PATH / f"team_{TEAM_ID}_tournaments.json"

with open(clean_file, "w", encoding="utf-8") as f:
    json.dump(clean_tournaments, f, ensure_ascii=False, indent=4)

# =====================================
# LOG FINAL
# =====================================

logger.info(f"Tournaments limpo salvo em: {clean_file}")
logger.info(f"TOTAL TOURNAMENTS: {len(clean_tournaments)}")
