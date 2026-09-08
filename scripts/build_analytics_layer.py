import logging
from pathlib import Path

import duckdb


# =====================================
# LOGGING
# =====================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# =====================================
# PATHS
# =====================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PROCESSED_PATH = PROJECT_ROOT / "data" / "processed"

DATABASE_PATH = PROJECT_ROOT / "data" / "vasco.duckdb"

SQL_VIEWS_PATH = PROJECT_ROOT / "sql" / "views"


# =====================================
# PARQUET TABLES
# =====================================

TABLES = {
    "matches": "matches.parquet",
    "teams": "teams.parquet",
    "players": "players.parquet",
    "lineups": "lineups.parquet",
    "statistics": "statistics.parquet",
    "player_statistics": "player_statistics.parquet",
}


# =====================================
# VALIDATE FILES
# =====================================

def validate_files():
    """
    Verifica se todos os arquivos Parquet
    necessários existem antes da construção.
    """

    logger.info("Validando arquivos Parquet...")

    missing_files = []

    for table_name, file_name in TABLES.items():

        file_path = PROCESSED_PATH / file_name

        if not file_path.exists():

            missing_files.append(str(file_path))

            logger.error(
                f"Arquivo ausente para tabela '{table_name}': "
                f"{file_path}"
            )

        else:

            logger.info(
                f"Arquivo encontrado para '{table_name}': "
                f"{file_path.name}"
            )

    if missing_files:

        raise FileNotFoundError(
            "Arquivos Parquet obrigatórios não encontrados:\n"
            + "\n".join(missing_files)
        )


# =====================================
# BUILD TABLES
# =====================================

def build_tables(conn):
    """
    Cria ou substitui as tabelas DuckDB
    a partir dos arquivos Parquet.
    """

    logger.info("Construindo tabelas DuckDB...")

    for table_name, file_name in TABLES.items():

        parquet_path = PROCESSED_PATH / file_name

        logger.info(
            f"Criando/atualizando tabela: {table_name}"
        )

        query = f"""
        CREATE OR REPLACE TABLE {table_name} AS
        SELECT *
        FROM read_parquet('{parquet_path.as_posix()}')
        """

        conn.execute(query)

        row_count = conn.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

        logger.info(
            f"Tabela '{table_name}' atualizada "
            f"com {row_count:,} registros"
        )


# =====================================
# EXECUTE VIEWS
# =====================================

def build_views(conn):
    """
    Executa todos os arquivos SQL da pasta
    sql/views para criar as views analíticas.
    """

    logger.info("Construindo views analíticas...")

    sql_files = sorted(SQL_VIEWS_PATH.glob("*.sql"))

    if not sql_files:

        raise FileNotFoundError(
            f"Nenhum arquivo SQL encontrado em: "
            f"{SQL_VIEWS_PATH}"
        )

    for sql_file in sql_files:

        logger.info(
            f"Executando view SQL: {sql_file.name}"
        )

        sql = sql_file.read_text(
            encoding="utf-8"
        )

        conn.execute(sql)

        logger.info(
            f"View criada/atualizada: {sql_file.stem}"
        )


# =====================================
# VALIDATE VIEWS
# =====================================

def validate_views(conn):
    """
    Verifica se as views analíticas do projeto
    foram criadas corretamente no DuckDB.
    """

    logger.info("Validando views...")

    expected_views = [
        "vw_vasco_matches",
        "vw_vasco_player_match_statistics",
        "vw_vasco_team_period_statistics",
        "vw_vasco_team_statistics",
    ]

    views = conn.execute("""
        SELECT view_name
        FROM duckdb_views()
        WHERE view_name LIKE 'vw_vasco_%'
        ORDER BY view_name
    """).fetchall()

    existing_views = [view[0] for view in views]

    missing_views = [
        view
        for view in expected_views
        if view not in existing_views
    ]

    if missing_views:

        raise RuntimeError(
            "Views não encontradas:\n"
            + "\n".join(missing_views)
        )

    logger.info("Views analíticas validadas:")

    for view_name in existing_views:

        logger.info(f" - {view_name}")

# =====================================
# MAIN
# =====================================

def main():

    logger.info("=" * 50)
    logger.info("BUILD ANALYTICS LAYER STARTED")
    logger.info("=" * 50)

    validate_files()

    logger.info(
        f"Conectando ao DuckDB: {DATABASE_PATH}"
    )

    conn = duckdb.connect(
        str(DATABASE_PATH)
    )

    try:

        build_tables(conn)

        build_views(conn)

        validate_views(conn)

    finally:

        conn.close()

        logger.info(
            "Conexão DuckDB encerrada."
        )

    logger.info("=" * 50)
    logger.info(
        "BUILD ANALYTICS LAYER FINISHED SUCCESSFULLY"
    )
    logger.info("=" * 50)


# =====================================
# ENTRY POINT
# =====================================

if __name__ == "__main__":

    main()