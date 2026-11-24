
import pandas as pd

matches = pd.read_parquet("data/processed/matches.parquet")
statistics = pd.read_parquet("data/processed/player_statistics.parquet")

matches["match_id"] = matches["match_id"].astype("int64")
statistics["match_id"] = statistics["match_id"].astype("int64")

matches["match_date"] = pd.to_datetime(matches["match_date"])

# Partidas de 2026
matches_2026 = matches[
    matches["match_date"].dt.year == 2026
]

match_ids_2026 = set(matches_2026["match_id"])
statistics_ids = set(statistics["match_id"])

# Comparações
with_statistics = match_ids_2026 & statistics_ids
without_statistics = match_ids_2026 - statistics_ids
orphan_statistics = statistics_ids - set(matches["match_id"])

print("\n===== COBERTURA 2026 =====")
print("Partidas cadastradas:", len(match_ids_2026))
print("Partidas com estatísticas:", len(with_statistics))
print("Partidas sem estatísticas:", len(without_statistics))
print("Cobertura percentual:",
      round(len(with_statistics) / len(match_ids_2026) * 100, 2), "%")

print("\n===== ESTATÍSTICAS SEM PARTIDA CADASTRADA =====")
print("Quantidade:", len(orphan_statistics))
print("IDs:", sorted(orphan_statistics))

print("\n===== PARTIDAS DE 2026 SEM ESTATÍSTICAS =====")
print("Primeiros 20 IDs:", sorted(without_statistics)[:20])
