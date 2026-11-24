
import json
import logging
from collections import Counter
from pathlib import Path

import pandas as pd

# =====================================
# CONFIG
# =====================================

YEAR = 2026

MATCHES_PATH = Path("data/processed/matches.parquet")
LINEUPS_PATH = Path("data/raw/lineups")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

# =====================================
# LOAD MATCHES
# =====================================

df = pd.read_parquet(
    MATCHES_PATH,
    columns=["match_id", "match_date"],
)

df["match_date"] = pd.to_datetime(
    df["match_date"],
    errors="coerce",
)

df["match_id"] = pd.to_numeric(
    df["match_id"],
    errors="coerce",
)

df = df.dropna(subset=["match_id", "match_date"])

df = df.loc[df["match_date"].dt.year == YEAR]

match_ids = set(df["match_id"].astype("int64"))

# =====================================
# COUNTERS
# =====================================

files_found = 0
valid_files = 0
invalid_files = 0
confirmed_files = 0
pending_files = 0

total_players = 0
starters = 0
substitutes = 0

players_with_stats = 0
players_without_stats = 0

metric_counter = Counter()
player_key_counter = Counter()
stat_key_counter = Counter()

# =====================================
# DIAGNOSTIC
# =====================================

for match_id in sorted(match_ids):

    file_path = LINEUPS_PATH / f"{match_id}.json"

    if not file_path.exists():
        continue

    files_found += 1

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("JSON não é um objeto")

        valid_files += 1

        if data.get("confirmed") is True:
            confirmed_files += 1
        else:
            pending_files += 1

        for side in ("home", "away"):

            team = data.get(side, {})

            if not isinstance(team, dict):
                continue

            for group in ("players", "substitutes"):

                entries = team.get(group) or []

                if not isinstance(entries, list):
                    continue

                for entry in entries:

                    if not isinstance(entry, dict):
                        continue

                    total_players += 1

                    if entry.get("substitute") is True:
                        substitutes += 1
                    elif entry.get("substitute") is False:
                        starters += 1
                    elif group == "substitutes":
                        substitutes += 1
                    else:
                        starters += 1

                    player = entry.get("player") or {}

                    if isinstance(player, dict):
                        player_key_counter.update(player.keys())

                    statistics = entry.get("statistics")

                    if isinstance(statistics, dict) and statistics:
                        players_with_stats += 1
                        stat_key_counter.update(statistics.keys())

                        metric_counter.update(
                            key for key in statistics.keys()
                            if key != "statisticsType"
                        )
                    else:
                        players_without_stats += 1

    except Exception as exc:
        invalid_files += 1
        logger.warning(
            "Arquivo inválido: %s | %s",
            file_path.name,
            exc,
        )

# =====================================
# REPORT
# =====================================

print("\n" + "=" * 55)
print("DIAGNÓSTICO DAS ESCALAÇÕES")
print("=" * 55)

print(f"Ano analisado: {YEAR}")
print(f"Partidas no Parquet: {len(match_ids)}")
print(f"Arquivos encontrados: {files_found}")
print(f"Arquivos válidos: {valid_files}")
print(f"Arquivos inválidos: {invalid_files}")
print(f"Escalações confirmadas: {confirmed_files}")
print(f"Escalações não confirmadas: {pending_files}")

print("\n--- JOGADORES ---")
print(f"Total de registros: {total_players}")
print(f"Titulares: {starters}")
print(f"Reservas: {substitutes}")
print(f"Com estatísticas: {players_with_stats}")
print(f"Sem estatísticas: {players_without_stats}")

print("\n--- MÉTRICAS ---")
print(f"Quantidade de métricas distintas: {len(metric_counter)}")

for metric, count in metric_counter.most_common():
    print(f"{metric}: {count}")

print("\n--- CAMPOS CADASTRAIS DOS JOGADORES ---")
for field, count in player_key_counter.most_common():
    print(f"{field}: {count}")

print("\n--- CAMPOS DE ESTATÍSTICAS ---")
for field, count in stat_key_counter.most_common():
    print(f"{field}: {count}")

print("\n" + "=" * 55)
