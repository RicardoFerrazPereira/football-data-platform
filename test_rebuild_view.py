import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

DATABASE_PATH = PROJECT_ROOT / "data" / "vasco.duckdb"
SQL_FILE = PROJECT_ROOT / "sql" / "views" / "vw_vasco_player_match_statistics.sql"

print(f"Banco: {DATABASE_PATH}")
print(f"SQL:   {SQL_FILE}")

sql = SQL_FILE.read_text(encoding="utf-8")

conn = duckdb.connect(str(DATABASE_PATH))

try:
    conn.execute(sql)

    result = conn.execute("""
        SELECT COUNT(*)
        FROM duckdb_views()
        WHERE view_name = 'vw_vasco_player_match_statistics'
    """).fetchone()[0]

    print(f"View encontrada: {result}")

    columns = conn.execute("""
        DESCRIBE vw_vasco_player_match_statistics
    """).fetchall()

    print(f"Quantidade de colunas: {len(columns)}")

finally:
    conn.close()