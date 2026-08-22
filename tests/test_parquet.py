import pandas as pd

# =========================
# LOAD PARQUET
# =========================

df = pd.read_parquet(
    "data/processed/matches.parquet"
)

# =========================
# PREVIEW
# =========================

print("\nHEAD:\n")

print(df.head())

# =========================
# INFO
# =========================

print("\nINFO:\n")

print(df.info())

# =========================
# SHAPE
# =========================

print("\nSHAPE:\n")

print(df.shape)

# =========================
# COLUMNS
# =========================

print("\nCOLUMNS:\n")

print(df.columns.tolist())