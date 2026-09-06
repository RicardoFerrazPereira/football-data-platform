from pathlib import Path

import duckdb


# =====================================
# PATHS
# =====================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_PATH = PROJECT_ROOT / "data" / "processed"


# =====================================
# PARQUET FILES
# =====================================

datasets = [
    "matches.parquet",
    "teams.parquet",
    "players.parquet",
    "lineups.parquet",
    "player_statistics.parquet",
    "statistics.parquet",
]


# =====================================
# DUCKDB CONNECTION
# =====================================

con = duckdb.connect()


print("\n================================")
print("DUCKDB DATASET TEST")
print("================================\n")


# =====================================
# TEST DATASETS
# =====================================

for dataset in datasets:

    file_path = PROCESSED_PATH / dataset

    print("--------------------------------")
    print(f"DATASET: {dataset}")
    print("--------------------------------")

    if not file_path.exists():

        print("❌ Arquivo não encontrado")
        print(f"Path: {file_path}\n")

        continue

    try:

        query = f"""
        SELECT COUNT(*) AS total_rows
        FROM read_parquet('{file_path.as_posix()}')
        """

        result = con.execute(query).fetchone()

        print("Status: ✅ OK")
        print(f"Total de registros: {result[0]}")

    except Exception as e:

        print("Status: ❌ ERROR")
        print(e)

    print()


# =====================================
# CLOSE CONNECTION
# =====================================

con.close()


print("================================")
print("TEST FINALIZADO")
print("================================")