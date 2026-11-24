
import pandas as pd

matches = pd.read_parquet("data/processed/matches.parquet")
statistics = pd.read_parquet("data/processed/player_statistics.parquet")

print("\n===== COLUNAS DE MATCHES =====")
print(matches.columns.tolist())

print("\n===== PERÍODO DAS PARTIDAS =====")

for column in matches.columns:
    if "date" in column.lower():
        dates = pd.to_datetime(matches[column], errors="coerce")
        print(f"{column}: {dates.min()} até {dates.max()}")

print("\n===== DISTRIBUIÇÃO POR ANO =====")

for column in matches.columns:
    if "date" in column.lower():
        dates = pd.to_datetime(matches[column], errors="coerce")
        print(dates.dt.year.value_counts().sort_index().to_string())
        break

print("\n===== SETE PARTIDAS SEM CORRESPONDÊNCIA =====")

orphan_ids = sorted(
    set(statistics["match_id"].unique())
    - set(matches["match_id"].unique())
)

print("IDs:", orphan_ids)
