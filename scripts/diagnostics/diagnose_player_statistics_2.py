
import pandas as pd

matches = pd.read_parquet("data/processed/matches.parquet")
statistics = pd.read_parquet("data/processed/player_statistics.parquet")

match_ids = set(matches["match_id"].dropna().astype(int))
statistics_ids = set(statistics["match_id"].dropna().astype(int))

missing = sorted(match_ids - statistics_ids)
orphan = sorted(statistics_ids - match_ids)

print("\n===== RESUMO =====")
print("Partidas no cadastro:", len(match_ids))
print("Partidas com estatísticas:", len(statistics_ids))
print("Partidas sem estatísticas:", len(missing))
print("Estatísticas sem partida correspondente:", len(orphan))

print("\nPrimeiros 15 IDs sem estatísticas:")
print(missing[:15])

print("\nPrimeiros 15 IDs sem correspondência:")
print(orphan[:15])
