import logging
import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


# ============================================================
# PIPELINE
# ============================================================

PIPELINE = [
    (
        "01 - Collect tournaments",
        "scripts/extract/collect_tournaments.py",
    ),
    (
        "02 - Collect seasons",
        "scripts/extract/collect_seasons.py",
    ),
    (
        "03 - Collect matches",
        "scripts/extract/collect_matches.py",
    ),
    (
        "04 - Transform matches",
        "scripts/transform/transform_matches.py",
    ),
    (
        "05 - Collect match details",
        "scripts/extract/collect_match_details.py",
    ),
    (
        "06 - Transform teams",
        "scripts/transform/transform_teams.py",
    ),
    (
        "07 - Collect lineups",
        "scripts/extract/collect_lineups.py",
    ),
    (
        "08 - Transform players",
        "scripts/transform/transform_players.py",
    ),
    (
        "09 - Transform lineups",
        "scripts/transform/transform_lineups.py",
    ),
    (
        "10 - Collect statistics",
        "scripts/extract/collect_statistics.py",
        ),
    (
        "11 - Transform statistics",
        "scripts/transform/transform_statistics.py",
    ),
    (
        "12 - Transform player statistics",
        "scripts/transform/transform_player_statistics.py",
    ),
    (
        "13 - Validate data",
        "validation/validate_data.py",
    ),
    (
        "14 - Build analytics layer",
        "scripts/build_analytics_layer.py",
    ),
]


# ============================================================
# EXECUTE STEP
# ============================================================

def run_step(
    step_number: int,
    name: str,
    script: str,
) -> None:
    """
    Executa uma etapa do pipeline.

    Se o script retornar código diferente de zero,
    o pipeline é interrompido.
    """

    script_path = PROJECT_ROOT / script

    # --------------------------------------------------------
    # CHECK SCRIPT
    # --------------------------------------------------------

    if not script_path.exists():
        raise FileNotFoundError(
            f"Script não encontrado: {script_path}"
        )

    # --------------------------------------------------------
    # LOG START
    # --------------------------------------------------------

    logger.info("=" * 70)
    logger.info(
        f"ETAPA {step_number}/{len(PIPELINE)}: {name}"
    )
    logger.info(f"Script: {script}")
    logger.info("=" * 70)

    start_time = time.perf_counter()

    # --------------------------------------------------------
    # EXECUTE SCRIPT
    # --------------------------------------------------------

    result = subprocess.run(
        [
            PYTHON,
            str(script_path),
        ],
        cwd=PROJECT_ROOT,
    )

    elapsed = time.perf_counter() - start_time

    # --------------------------------------------------------
    # CHECK RESULT
    # --------------------------------------------------------

    if result.returncode != 0:
        logger.error(
            f"ETAPA {step_number}/{len(PIPELINE)} FALHOU: "
            f"{name}"
        )

        logger.error(
            f"Tempo até a falha: {elapsed:.2f} segundos"
        )

        raise RuntimeError(
            f"Pipeline interrompido na etapa "
            f"{step_number}: {name}"
        )

    # --------------------------------------------------------
    # LOG SUCCESS
    # --------------------------------------------------------

    logger.info(
        f"ETAPA {step_number}/{len(PIPELINE)} "
        f"CONCLUÍDA: {name}"
    )

    logger.info(
        f"Tempo da etapa: {elapsed:.2f} segundos"
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Executa todas as etapas do pipeline na ordem definida.
    """

    pipeline_start = time.perf_counter()

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    logger.info("=" * 70)
    logger.info("VASCO EM DADOS - DATA PIPELINE")
    logger.info("PIPELINE STARTED")
    logger.info("=" * 70)

    logger.info(
        f"Projeto: {PROJECT_ROOT}"
    )

    logger.info(
        f"Python: {PYTHON}"
    )

    logger.info(
        f"Total de etapas: {len(PIPELINE)}"
    )

    # --------------------------------------------------------
    # EXECUTE PIPELINE
    # --------------------------------------------------------

    try:

        for step_number, (name, script) in enumerate(
            PIPELINE,
            start=1,
        ):
            run_step(
                step_number,
                name,
                script,
            )

    # --------------------------------------------------------
    # PIPELINE ERROR
    # --------------------------------------------------------

    except Exception as error:

        total_elapsed = (
            time.perf_counter()
            - pipeline_start
        )

        logger.error("=" * 70)
        logger.error("PIPELINE FAILED")
        logger.error(f"Erro: {error}")

        logger.error(
            f"Tempo total até a falha: "
            f"{total_elapsed:.2f} segundos"
        )

        logger.error("=" * 70)

        sys.exit(1)

    # --------------------------------------------------------
    # PIPELINE SUCCESS
    # --------------------------------------------------------

    total_elapsed = (
        time.perf_counter()
        - pipeline_start
    )

    logger.info("=" * 70)
    logger.info("PIPELINE FINISHED SUCCESSFULLY")

    logger.info(
        f"Tempo total: "
        f"{total_elapsed:.2f} segundos"
    )

    logger.info("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()