
from pathlib import Path
import duckdb

# Caminhos do projeto
PROJECT_DIR = Path(__file__).resolve().parent

DB_PATH = PROJECT_DIR / "data" / "vasco.duckdb"

SQL_PATH = (
    PROJECT_DIR
    / "sql"
    / "views"
    / "vw_vasco_player_season_metrics_corrigida.sql"
)

def main():
    # Verifica os arquivos antes de conectar
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Banco não encontrado: {DB_PATH}")

    if not SQL_PATH.exists():
        raise FileNotFoundError(f"Arquivo SQL não encontrado: {SQL_PATH}")

    print(f"Banco: {DB_PATH}")
    print(f"SQL: {SQL_PATH}")

    # Lê o SQL completo
    sql = SQL_PATH.read_text(encoding="utf-8")

    print(f"\nSQL carregado: {len(sql):,} caracteres")
    print("Executando no DuckDB...")

    # Conecta ao banco existente
    con = duckdb.connect(str(DB_PATH))

    try:
        # Executa a definição completa da view
        con.execute(sql)

        print("\nView criada/substituída com sucesso!")

        # Valida a existência e consulta a view
        resultado = con.execute("""
            SELECT
                COUNT(*) AS total_linhas,
                COUNT(position) AS registros_com_posicao
            FROM main.vw_vasco_player_season_metrics
        """).fetchone()

        print("\nValidação:")
        print(f"Total de linhas: {resultado[0]:,}")
        print(f"Registros com posição: {resultado[1]:,}")

    finally:
        con.close()
        print("\nConexão com o banco encerrada.")


if __name__ == "__main__":
    main()
