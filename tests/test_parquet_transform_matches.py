import pandas as pd

df = pd.read_parquet("data/processed/matches.parquet")

print("TOTAL DE PARTIDAS:", len(df))
print("IDs ÚNICOS:", df["match_id"].nunique())
print("PARTIDAS SEM ID:", df["match_id"].isna().sum())
print("PARTIDAS SEM DATA:", df["match_date"].isna().sum())

print("\nPERÍODO:")
print(df["match_date"].min(), "→", df["match_date"].max())

print("\nTIPOS DE DADOS:")
print(df.dtypes)

print("\nPRIMEIRAS PARTIDAS:")
print(df.head())
