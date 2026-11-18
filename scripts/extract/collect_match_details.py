
import argparse
import json
import logging
import os
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


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
# CONFIG
# =====================================

BASE_URL = "https://www.sofascore.com/api/v1"

MATCHES_PATH = Path("data/processed/matches.parquet")

SAVE_PATH = Path("data/raw/match_details")

DEFAULT_FILTER_YEAR = 2026

SLEEP_BETWEEN_REQUESTS = 1
MAX_RETRIES = 3
NAVIGATION_TIMEOUT = 60000

SAVE_PATH.mkdir(parents=True, exist_ok=True)


# =====================================
# EXCEPTIONS
# =====================================

class FatalHTTPError(Exception):
    """Erro HTTP que deve interromper toda a coleta."""
    pass


class NonRetryableHTTPError(Exception):
    """Erro HTTP que não deve gerar novas tentativas."""
    pass


class CollectionError(Exception):
    """Falha definitiva na coleta de uma partida."""
    pass


# =====================================
# ARGUMENTS
# =====================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Coleta detalhes das partidas do Sofascore."
    )

    parser.add_argument(
        "year",
        nargs="?",
        type=int,
        default=DEFAULT_FILTER_YEAR,
        help=f"Ano das partidas. Padrão: {DEFAULT_FILTER_YEAR}",
    )

    return parser.parse_args()


# =====================================
# LOAD MATCHES
# =====================================

def load_matches(year: int) -> pd.DataFrame:

    if not MATCHES_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {MATCHES_PATH}\n"
            "Execute primeiro a transformação das partidas."
        )

    df = pd.read_parquet(MATCHES_PATH)

    logger.info(f"Matches carregados: {len(df)}")

    required_columns = {"match_id", "match_date"}

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Colunas obrigatórias ausentes no Parquet: "
            f"{sorted(missing_columns)}"
        )

    # Normaliza as datas para permitir o filtro por ano.
    df["match_date"] = pd.to_datetime(
        df["match_date"],
        errors="coerce",
        utc=True,
    )

    invalid_dates = df["match_date"].isna().sum()

    if invalid_dates:
        logger.warning(
            f"Partidas com data inválida: {invalid_dates}"
        )

    df = df[
        df["match_date"].dt.year == year
    ].copy()

    # Remove partidas sem identificador.
    df = df[df["match_id"].notna()].copy()

    # Evita requisições duplicadas.
    df = df.drop_duplicates(subset=["match_id"])

    logger.info(
        f"Matches selecionados para {year}: {len(df)}"
    )

    return df


# =====================================
# VALIDATE EXISTING JSON
# =====================================

def is_valid_json_file(file_path: Path) -> bool:
    """
    Verifica se o arquivo existente contém um JSON válido
    com a estrutura esperada pelo endpoint de detalhes.
    """

    if not file_path.exists():
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return False

        event = data.get("event")

        if not isinstance(event, dict):
            return False

        return True

    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return False


# =====================================
# SAVE RAW JSON
# =====================================

def save_json_atomic(data: dict, output_file: Path):
    """
    Salva primeiro em arquivo temporário.
    Somente depois substitui o arquivo definitivo.
    """

    temp_file = output_file.with_name(
        output_file.name + ".tmp"
    )

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        os.replace(temp_file, output_file)

    finally:
        if temp_file.exists():
            temp_file.unlink()


# =====================================
# FETCH WITH RETRY
# =====================================

def fetch_with_retry(page, url: str) -> dict | None:
    """
    Acessa o endpoint utilizando Playwright.

    Retorna:
        dict: resposta JSON válida.
        None: partida não encontrada (404).

    Interrompe a coleta:
        HTTP 403 ou HTTP 429.
    """

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=NAVIGATION_TIMEOUT,
            )

            if response is None:
                raise CollectionError(
                    "Navegação não retornou uma resposta HTTP."
                )

            status_code = response.status

            # ---------------------------------
            # SUCCESS
            # ---------------------------------

            if status_code == 200:

                data = response.json()

                if not isinstance(data, dict):
                    raise CollectionError(
                        "Resposta JSON não é um objeto."
                    )

                event = data.get("event")

                if not isinstance(event, dict):
                    raise CollectionError(
                        "Resposta não contém o objeto 'event' esperado."
                    )

                return data

            # ---------------------------------
            # NOT FOUND
            # ---------------------------------

            if status_code == 404:
                logger.warning(
                    "HTTP 404 — partida não encontrada."
                )
                return None

            # ---------------------------------
            # FATAL ERRORS
            # ---------------------------------

            if status_code in (403, 429):
                raise FatalHTTPError(
                    f"HTTP {status_code} — acesso negado "
                    "ou limite de requisições atingido."
                )

            # ---------------------------------
            # NON-RETRYABLE CLIENT ERRORS
            # ---------------------------------

            if 400 <= status_code < 500:
                raise NonRetryableHTTPError(
                    f"HTTP {status_code} — erro de requisição."
                )

            # ---------------------------------
            # SERVER ERRORS
            # ---------------------------------

            if status_code >= 500:
                raise CollectionError(
                    f"HTTP {status_code} — erro no servidor."
                )

            raise CollectionError(
                f"Status HTTP inesperado: {status_code}"
            )

        except FatalHTTPError:
            raise

        except NonRetryableHTTPError:
            raise

        except (
            PlaywrightTimeoutError,
            PlaywrightError,
            CollectionError,
            ValueError,
        ) as error:

            logger.warning(
                f"Tentativa {attempt}/{MAX_RETRIES} falhou: {error}"
            )

            if attempt < MAX_RETRIES:
                wait_time = 2 ** (attempt - 1)

                logger.info(
                    f"Aguardando {wait_time}s para tentar novamente..."
                )

                time.sleep(wait_time)

        except Exception as error:

            logger.warning(
                f"Erro inesperado na tentativa "
                f"{attempt}/{MAX_RETRIES}: {error}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(2 ** (attempt - 1))

    raise CollectionError(
        f"Falha após {MAX_RETRIES} tentativas: {url}"
    )


# =====================================
# COLLECT MATCH DETAILS
# =====================================

def collect_match_details(page, df_matches: pd.DataFrame):

    total = len(df_matches)

    stats = {
        "total": total,
        "existing_valid": 0,
        "collected": 0,
        "not_found": 0,
        "failed": 0,
        "invalid_existing": 0,
    }

    for i, row in enumerate(
        df_matches.itertuples(index=False),
        start=1,
    ):

        match_id = int(row.match_id)

        output_file = SAVE_PATH / f"{match_id}.json"

        logger.info(
            f"[{i}/{total}] Match ID: {match_id}"
        )

        # ---------------------------------
        # CHECK EXISTING FILE
        # ---------------------------------

        if output_file.exists():

            if is_valid_json_file(output_file):

                stats["existing_valid"] += 1

                logger.info(
                    "Arquivo existente e válido — pulando."
                )

                continue

            stats["invalid_existing"] += 1

            logger.warning(
                "Arquivo existente inválido — será feita nova coleta."
            )

        # ---------------------------------
        # REQUEST
        # ---------------------------------

        url = f"{BASE_URL}/event/{match_id}"

        try:

            data = fetch_with_retry(page, url)

            if data is None:

                stats["not_found"] += 1

                logger.warning(
                    f"Partida {match_id} não encontrada."
                )

                if i < total:
                    time.sleep(SLEEP_BETWEEN_REQUESTS)

                continue

            # ---------------------------------
            # SAVE RAW JSON
            # ---------------------------------

            save_json_atomic(data, output_file)

            stats["collected"] += 1

            logger.info(
                f"Detalhes salvos: {output_file.name}"
            )

        except FatalHTTPError:
            logger.exception(
                "Erro crítico de acesso. Coleta interrompida."
            )
            raise

        except (
            NonRetryableHTTPError,
            CollectionError,
        ) as error:

            stats["failed"] += 1

            logger.error(
                f"Falha na partida {match_id}: {error}"
            )

        except Exception:

            stats["failed"] += 1

            logger.exception(
                f"Erro inesperado na partida {match_id}."
            )

        # ---------------------------------
        # RATE LIMIT
        # ---------------------------------

        if i < total:
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    return stats


# =====================================
# FINAL VALIDATION
# =====================================

def count_valid_files(df_matches: pd.DataFrame) -> int:

    valid_count = 0

    for match_id in df_matches["match_id"]:

        output_file = SAVE_PATH / f"{int(match_id)}.json"

        if is_valid_json_file(output_file):
            valid_count += 1

    return valid_count


# =====================================
# MAIN
# =====================================

def main():

    args = parse_arguments()

    filter_year = args.year

    logger.info("=" * 60)
    logger.info("COLETA DE DETALHES DAS PARTIDAS")
    logger.info("=" * 60)

    logger.info(f"Ano selecionado: {filter_year}")
    logger.info(f"Diretório de saída: {SAVE_PATH}")

    df_matches = load_matches(filter_year)

    if df_matches.empty:
        logger.warning(
            f"Nenhuma partida encontrada para {filter_year}."
        )
        return

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=False
        )

        context = browser.new_context(
            locale="pt-BR"
        )

        page = context.new_page()

        page.set_default_navigation_timeout(
            NAVIGATION_TIMEOUT
        )

        try:

            stats = collect_match_details(
                page,
                df_matches,
            )

        finally:

            context.close()
            browser.close()

    # =================================
    # FINAL REPORT
    # =================================

    valid_files = count_valid_files(df_matches)

    logger.info("")
    logger.info("=" * 60)
    logger.info("COLETA DE DETALHES FINALIZADA")
    logger.info("=" * 60)

    logger.info(f"Partidas selecionadas: {stats['total']}")
    logger.info(
        f"Arquivos existentes válidos: {stats['existing_valid']}"
    )
    logger.info(
        f"Novas partidas coletadas: {stats['collected']}"
    )
    logger.info(
        f"Partidas não encontradas (404): {stats['not_found']}"
    )
    logger.info(
        f"Partidas com falha: {stats['failed']}"
    )
    logger.info(
        f"Arquivos existentes inválidos identificados: "
        f"{stats['invalid_existing']}"
    )
    logger.info(
        f"Arquivos válidos ao final: {valid_files}"
    )

    logger.info(f"ANO: {filter_year}")
    logger.info(f"ARQUIVOS: {SAVE_PATH}")


if __name__ == "__main__":
    main()
