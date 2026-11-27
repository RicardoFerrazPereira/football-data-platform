
from pathlib import Path
import duckdb

processed_path = Path("data/processed")

files = [
    "matches.parquet",
    "teams.parquet",
    "players.parquet",
    "lineups.parquet",
    "statistics.parquet",
    "player_statistics.parquet",
]

con = duckdb.connect()

try:
    for file_name in files:
        file_path = (processed_path / file_name).resolve()

        query = """
            SELECT COUNT(*)
            FROM read_parquet(?)
        """

        total = con.execute(query, [str(file_path)]).fetchone()[0]

        print(f"{file_name}: {total:,} registros")

finally:
    con.close()
