
import pandas as pd

path = "data/processed/player_statistics.parquet"

df = pd.read_parquet(path)

key_columns = [
    "match_id",
    "team_id",
    "player_id",
    "statistic_name"
]

print("\n===== VALIDAÇÃO DE GRANULARIDADE =====")

duplicates = df.duplicated(
    subset=key_columns,
    keep=False
)

print(f"Total de registros: {len(df)}")
print(f"Chaves duplicadas: {duplicates.sum()}")

if duplicates.any():
    print("\nExemplos de chaves duplicadas:")
    print(
        df.loc[duplicates]
        .sort_values(key_columns)
        .head(20)
        .to_string(index=False)
    )

print("\n===== VALIDAÇÃO DE VALORES =====")

print(
    "Diferenças entre value e value_numeric:",
    (~df["value"].eq(df["value_numeric"])).sum()
)

print(
    "Valores numéricos nulos:",
    df["value_numeric"].isna().sum()
)

print("\n===== COBERTURA =====")

print("Partidas:", df["match_id"].nunique())
print("Equipes:", df["team_id"].nunique())
print("Jogadores:", df["player_id"].nunique())
print("Métricas:", df["statistic_name"].nunique())

print("\n===== REGISTROS POR MÉTRICA =====")

print(df["statistic_name"].value_counts().to_string())
