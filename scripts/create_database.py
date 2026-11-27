from pathlib import Path

import duckdb


# =====================================
# PATHS
# =====================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_PATH = PROJECT_ROOT / "data" / "processed"

DATABASE_PATH = (
    PROJECT_ROOT
    / "analytics"
    / "database"
    / "football.duckdb"
)

DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


# =====================================
# DATASETS
# =====================================

datasets = {
    "matches": "matches.parquet",
    "teams": "teams.parquet",
    "players": "players.parquet",
    "lineups": "lineups.parquet",
    "player_statistics": "player_statistics.parquet",
    "statistics": "statistics.parquet",
}


# =====================================
# CREATE CONNECTION
# =====================================

print("\n================================")
print("CREATING DUCKDB DATABASE")
print("================================\n")

print(f"Database: {DATABASE_PATH}\n")

con = duckdb.connect(
    str(DATABASE_PATH)
)


# =====================================
# CREATE VIEWS
# =====================================

for view_name, file_name in datasets.items():

    file_path = PROCESSED_PATH / file_name

    print("--------------------------------")
    print(f"Creating view: {view_name}")
    print("--------------------------------")

    if not file_path.exists():

        raise FileNotFoundError(
            f"Dataset não encontrado: {file_path}"
        )

    query = f"""
    CREATE OR REPLACE VIEW {view_name} AS
    SELECT *
    FROM read_parquet('{file_path.as_posix()}');
    """

    con.execute(query)

    total_rows = con.execute(
        f"SELECT COUNT(*) FROM {view_name}"
    ).fetchone()[0]

    print("Status: OK")
    print(f"Rows: {total_rows}\n")


# =====================================
# LIST VIEWS
# =====================================

print("================================")
print("DATABASE OBJECTS")
print("================================\n")

objects = con.execute("""
    SELECT
        table_name,
        table_type
    FROM information_schema.tables
    WHERE table_schema = 'main'
    ORDER BY table_name
""").fetchall()

for table_name, table_type in objects:

    print(
        f"{table_type}: {table_name}"
    )


# =====================================
# CLOSE
# =====================================

con.close()


print("\n================================")
print("DATABASE CREATED SUCCESSFULLY")
print("================================")