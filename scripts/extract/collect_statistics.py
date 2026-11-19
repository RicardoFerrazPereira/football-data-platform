
# =============================================================================
# collect_statistics.py
# =============================================================================
# Coleta estatísticas das partidas do SofaScore utilizando Playwright.
#
# Fluxo:
#
#   matches.parquet
#        ↓
#   filtro por ano
#        ↓
#   seleção opcional por --limit ou --match-id
#        ↓
#   consulta ao endpoint de estatísticas
#        ↓
#   JSON bruto em data/raw/statistics
#
# O processo é incremental:
# - arquivos JSON válidos existentes são ignorados;
# - arquivos inválidos são coletados novamente;
# - HTTP 404 é tratado como estatísticas não encontradas;
# - HTTP 403/429 interrompe a coleta;
# - erros técnicos e HTTP 5xx podem ser repetidos;
# - arquivos JSON são gravados atomicamente.
#
# Uso:
#
#   python scripts/extract/collect_statistics.py 2026
#
# Teste limitado:
#
#   python scripts/extract/collect_statistics.py 2026 --limit 5
#
# Teste de uma partida específica:
#
#   python scripts/extract/collect_statistics.py 2026 --match-id 15138021
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import pandas as pd

from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

BASE_URL = "https://www.sofascore.com/api/v1/event"

MATCHES_PATH = Path("data/processed/matches.parquet")

SAVE_PATH = Path("data/raw/statistics")

DEFAULT_FILTER_YEAR = 2026

SLEEP_BETWEEN_REQUESTS = 2

MAX_RETRIES = 3

NAVIGATION_TIMEOUT = 30_000

HEADLESS = False


# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# =============================================================================
# EXCEÇÕES PERSONALIZADAS
# =============================================================================

class FatalHTTPError(Exception):
    """
    Erro HTTP que deve interromper imediatamente a coleta.

    Exemplos:
    - HTTP 403
    - HTTP 429
    """

    pass


class NonRetryableHTTPError(Exception):
    """
    Erro HTTP 4xx que não deve ser repetido.
    """

    pass


class CollectionError(Exception):
    """
    Erro técnico que pode ser submetido à política de retry.
    """

    pass


# =============================================================================
# ARGUMENTOS DA LINHA DE COMANDO
# =============================================================================

def parse_arguments() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Coleta estatísticas das partidas do SofaScore."
    )

    parser.add_argument(
        "year",
        nargs="?",
        type=int,
        default=DEFAULT_FILTER_YEAR,
        help=f"Ano das partidas. Padrão: {DEFAULT_FILTER_YEAR}.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de partidas processadas.",
    )

    parser.add_argument(
        "--match-id",
        type=int,
        default=None,
        help="Processa somente uma partida específica. Tem prioridade sobre --limit.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit deve ser maior que zero.")

    if args.match_id is not None and args.match_id <= 0:
        parser.error("--match-id deve ser maior que zero.")

    return args


# =============================================================================
# CARREGAMENTO DAS PARTIDAS
# =============================================================================

def load_matches(year: int) -> pd.DataFrame:
    """
    Carrega matches.parquet, valida as colunas e filtra pelo ano.
    """

    if not MATCHES_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de partidas não encontrado: {MATCHES_PATH}"
        )

    df = pd.read_parquet(MATCHES_PATH)

    logging.info(
        "Matches carregados: %s",
        len(df),
    )

    required_columns = {
        "match_id",
        "match_date",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes no arquivo de partidas: "
            f"{sorted(missing_columns)}"
        )

    df["match_date"] = pd.to_datetime(
        df["match_date"],
        utc=True,
        errors="coerce",
    )

    df = df[df["match_date"].notna()].copy()

    df = df[df["match_date"].dt.year == year].copy()

    df["match_id"] = pd.to_numeric(
        df["match_id"],
        errors="coerce",
    )

    df = df[df["match_id"].notna()].copy()

    df["match_id"] = df["match_id"].astype("int64")

    df = df.drop_duplicates(
        subset=["match_id"],
        keep="first",
    )

    df = df.sort_values(
        by=["match_date", "match_id"],
        ascending=[True, True],
    ).reset_index(drop=True)

    logging.info(
        "Matches selecionados para %s: %s",
        year,
        len(df),
    )

    return df


# =============================================================================
# VALIDAÇÃO ESTRUTURAL DO JSON
# =============================================================================

def is_valid_statistics_json(data: Any) -> bool:
    """
    Valida a estrutura mínima da resposta do endpoint de estatísticas.

    Estrutura esperada:

        statistics
            └── period
                 └── groups
                      └── statisticsItems

    Não exige homeTotal ou awayTotal, pois esses campos não aparecem
    necessariamente em todos os indicadores.
    """

    if not isinstance(data, dict):
        return False

    statistics = data.get("statistics")

    if not isinstance(statistics, list):
        return False

    for period in statistics:

        if not isinstance(period, dict):
            return False

        if not isinstance(period.get("period"), str):
            return False

        groups = period.get("groups")

        if not isinstance(groups, list):
            return False

        for group in groups:

            if not isinstance(group, dict):
                return False

            if not isinstance(group.get("groupName"), str):
                return False

            items = group.get("statisticsItems")

            if not isinstance(items, list):
                return False

            for item in items:

                if not isinstance(item, dict):
                    return False

                required_fields = {
                    "key",
                    "name",
                    "home",
                    "away",
                }

                if not required_fields.issubset(item):
                    return False

    return True


# =============================================================================
# CARREGAMENTO DE JSON EXISTENTE
# =============================================================================

def load_existing_json(
    output_file: Path,
) -> tuple[bool, dict[str, Any] | None]:
    """
    Carrega e valida um JSON de estatísticas existente.

    Retorna:

        (True, data)  -> arquivo válido.
        (False, None) -> arquivo inexistente ou inválido.
    """

    if not output_file.exists():
        return False, None

    try:

        with output_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:

        logging.warning(
            "Arquivo JSON inválido: %s | Erro: %s",
            output_file,
            exc,
        )

        return False, None

    if not is_valid_statistics_json(data):

        logging.warning(
            "Arquivo JSON com estrutura inválida: %s",
            output_file,
        )

        return False, None

    return True, data


# =============================================================================
# REQUISIÇÃO DE ESTATÍSTICAS
# =============================================================================

def fetch_statistics(
    page: Any,
    match_id: int,
) -> dict[str, Any] | None:
    """
    Consulta as estatísticas de uma partida utilizando Playwright.

    Retorna:
        dict -> resposta JSON válida.
        None -> HTTP 404.

    Levanta:
        FatalHTTPError para HTTP 403/429.
        NonRetryableHTTPError para outros 4xx.
        CollectionError para erros técnicos.
    """

    url = f"{BASE_URL}/{match_id}/statistics"

    try:

        response = page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=NAVIGATION_TIMEOUT,
        )

    except PlaywrightTimeoutError as exc:

        raise CollectionError(
            f"Timeout ao consultar Match ID {match_id}"
        ) from exc

    except Exception as exc:

        raise CollectionError(
            f"Erro de navegação no Match ID {match_id}: {exc}"
        ) from exc

    if response is None:

        raise CollectionError(
            f"Nenhuma resposta HTTP para Match ID {match_id}"
        )

    status = response.status

    # -------------------------------------------------------------------------
    # HTTP 200
    # -------------------------------------------------------------------------

    if status == 200:

        try:

            data = response.json()

        except Exception as exc:

            raise CollectionError(
                f"Resposta não pôde ser convertida para JSON "
                f"(Match ID {match_id})"
            ) from exc

        if not is_valid_statistics_json(data):

            raise CollectionError(
                f"JSON de estatísticas com estrutura inválida "
                f"(Match ID {match_id})"
            )

        return data

    # -------------------------------------------------------------------------
    # HTTP 404
    # -------------------------------------------------------------------------

    if status == 404:

        return None

    # -------------------------------------------------------------------------
    # HTTP 403 / 429
    # -------------------------------------------------------------------------

    if status in (403, 429):

        raise FatalHTTPError(
            f"HTTP {status} para Match ID {match_id}"
        )

    # -------------------------------------------------------------------------
    # OUTROS ERROS 4XX
    # -------------------------------------------------------------------------

    if 400 <= status < 500:

        raise NonRetryableHTTPError(
            f"HTTP {status} para Match ID {match_id}"
        )

    # -------------------------------------------------------------------------
    # ERROS 5XX
    # -------------------------------------------------------------------------

    if 500 <= status < 600:

        raise CollectionError(
            f"HTTP {status} para Match ID {match_id}"
        )

    # -------------------------------------------------------------------------
    # STATUS INESPERADO
    # -------------------------------------------------------------------------

    raise CollectionError(
        f"Status HTTP inesperado {status} "
        f"para Match ID {match_id}"
    )


# =============================================================================
# RETRY DA CONSULTA
# =============================================================================

def fetch_with_retry(
    page: Any,
    match_id: int,
) -> tuple[str, dict[str, Any] | None]:
    """
    Executa a consulta aplicando a política de retry.

    Retorna:

        ("ok", data)       -> sucesso.
        ("not_found", None) -> HTTP 404.
        ("error", None)    -> falha não recuperável para a partida.

    HTTP 403/429 são propagados para interromper a coleta.
    """

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            data = fetch_statistics(
                page,
                match_id,
            )

            if data is None:

                return "not_found", None

            return "ok", data

        except FatalHTTPError:

            raise

        except NonRetryableHTTPError as exc:

            logging.error(
                "Erro não recuperável | Match ID: %s | %s",
                match_id,
                exc,
            )

            return "error", None

        except CollectionError as exc:

            logging.warning(
                "Tentativa %s/%s falhou | Match ID: %s | %s",
                attempt,
                MAX_RETRIES,
                match_id,
                exc,
            )

            if attempt < MAX_RETRIES:

                wait_seconds = attempt

                logging.info(
                    "Aguardando %s segundo(s) antes da nova tentativa...",
                    wait_seconds,
                )

                time.sleep(wait_seconds)

            else:

                logging.error(
                    "Todas as tentativas falharam | Match ID: %s",
                    match_id,
                )

    return "error", None


# =============================================================================
# SALVAMENTO ATÔMICO
# =============================================================================

def save_json_atomic(
    data: dict[str, Any],
    output_file: Path,
) -> None:
    """
    Salva o JSON utilizando arquivo temporário e substituição atômica.
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = output_file.with_suffix(
        output_file.suffix + ".tmp"
    )

    try:

        with temp_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        temp_file.replace(output_file)

    except Exception:

        if temp_file.exists():
            temp_file.unlink()

        raise


# =============================================================================
# PROCESSAMENTO DE UMA PARTIDA
# =============================================================================

def process_match(
    page: Any,
    match_id: int,
) -> str:
    """
    Processa uma partida.

    Regras:

    1. JSON existente e válido:
       ignora a partida.

    2. JSON inexistente:
       realiza nova coleta.

    3. JSON inválido:
       realiza nova coleta.

    4. HTTP 404:
       registra estatísticas não encontradas.

    5. HTTP 200 com estrutura válida:
       salva o JSON bruto atomicamente.
    """

    output_file = SAVE_PATH / f"{match_id}.json"

    file_exists, existing_data = load_existing_json(
        output_file
    )

    # -------------------------------------------------------------------------
    # ARQUIVO EXISTENTE E VÁLIDO
    # -------------------------------------------------------------------------

    if file_exists and existing_data is not None:

        logging.info(
            "Arquivo válido já existe — pulando: %s",
            output_file.name,
        )

        return "skipped"

    # -------------------------------------------------------------------------
    # ARQUIVO INEXISTENTE OU INVÁLIDO
    # -------------------------------------------------------------------------

    logging.info(
        "Arquivo inexistente ou inválido — realizando nova coleta."
    )

    # -------------------------------------------------------------------------
    # CONSULTA AO SOFASCORE
    # -------------------------------------------------------------------------

    status, data = fetch_with_retry(
        page,
        match_id,
    )

    if status == "not_found":

        logging.warning(
            "Estatísticas não encontradas (HTTP 404)."
        )

        return "not_found"

    if status == "error" or data is None:

        logging.error(
            "Falha técnica na coleta."
        )

        return "failed"

    # -------------------------------------------------------------------------
    # SALVAMENTO
    # -------------------------------------------------------------------------

    save_json_atomic(
        data,
        output_file,
    )

    logging.info(
        "Novas estatísticas coletadas e salvas: %s",
        output_file.name,
    )

    return "new"


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def main() -> None:
    """
    Executa o processo completo de coleta de estatísticas.
    """

    args = parse_arguments()

    SAVE_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    logging.info("=" * 60)
    logging.info("COLETA DE ESTATÍSTICAS")
    logging.info("=" * 60)

    logging.info(
        "Ano selecionado: %s",
        args.year,
    )

    logging.info(
        "Diretório de saída: %s",
        SAVE_PATH,
    )

    # -------------------------------------------------------------------------
    # CARREGAMENTO DAS PARTIDAS
    # -------------------------------------------------------------------------

    matches = load_matches(
        args.year
    )

    # -------------------------------------------------------------------------
    # SELEÇÃO POR MATCH ID
    #
    # --match-id tem prioridade sobre --limit.
    # -------------------------------------------------------------------------

    if args.match_id is not None:

        matches = matches[
            matches["match_id"] == args.match_id
        ].copy()

        if matches.empty:

            raise ValueError(
                f"Match ID {args.match_id} não encontrado "
                f"entre as partidas de {args.year}."
            )

        logging.info(
            "Modo de teste: match-id=%s | Partidas selecionadas: 1",
            args.match_id,
        )

    # -------------------------------------------------------------------------
    # SELEÇÃO POR LIMITE
    # -------------------------------------------------------------------------

    elif args.limit is not None:

        available_matches = len(matches)

        matches = matches.head(
            args.limit
        ).copy()

        logging.info(
            "Modo de teste: limit=%s | "
            "Partidas disponíveis=%s | "
            "Partidas selecionadas=%s",
            args.limit,
            available_matches,
            len(matches),
        )

    # -------------------------------------------------------------------------
    # EXECUÇÃO NORMAL
    # -------------------------------------------------------------------------

    else:

        logging.info(
            "Modo normal | Todas as partidas do ano serão processadas: %s",
            len(matches),
        )

    # -------------------------------------------------------------------------
    # CONTADORES
    # -------------------------------------------------------------------------

    counters = {
        "new": 0,
        "skipped": 0,
        "not_found": 0,
        "failed": 0,
    }

    total_matches = len(matches)

    # -------------------------------------------------------------------------
    # NÃO ABRE O NAVEGADOR SE NÃO HOUVER PARTIDAS.
    # -------------------------------------------------------------------------

    if total_matches == 0:

        logging.warning(
            "Nenhuma partida encontrada para processamento."
        )

        return

    # -------------------------------------------------------------------------
    # INICIALIZA PLAYWRIGHT
    # -------------------------------------------------------------------------

    with sync_playwright() as playwright:

        browser = None
        context = None
        page = None

        try:

            browser = playwright.chromium.launch(
                headless=HEADLESS
            )

            context = browser.new_context(
                locale="pt-BR"
            )

            page = context.new_page()

            page.set_default_timeout(
                NAVIGATION_TIMEOUT
            )

            # -----------------------------------------------------------------
            # LOOP PRINCIPAL
            # -----------------------------------------------------------------

            for index, row in enumerate(
                matches.itertuples(index=False),
                start=1,
            ):

                match_id = int(row.match_id)

                logging.info(
                    "[%s/%s] Match ID: %s",
                    index,
                    total_matches,
                    match_id,
                )

                try:

                    result = process_match(
                        page,
                        match_id,
                    )

                    counters[result] += 1

                except FatalHTTPError:

                    logging.critical(
                        "Erro fatal encontrado. Coleta interrompida."
                    )

                    raise

                except Exception as exc:

                    logging.exception(
                        "Erro inesperado no Match ID %s: %s",
                        match_id,
                        exc,
                    )

                    counters["failed"] += 1

                # -------------------------------------------------------------
                # INTERVALO ENTRE PARTIDAS
                # -------------------------------------------------------------

                if index < total_matches:

                    page.wait_for_timeout(
                        SLEEP_BETWEEN_REQUESTS * 1000
                    )

        finally:

            if page is not None:
                page.close()

            if context is not None:
                context.close()

            if browser is not None:
                browser.close()

    # -------------------------------------------------------------------------
    # RELATÓRIO FINAL
    # -------------------------------------------------------------------------

    logging.info("")
    logging.info("=" * 60)
    logging.info("COLETA DE ESTATÍSTICAS FINALIZADA")
    logging.info("=" * 60)

    logging.info(
        "Ano: %s",
        args.year,
    )

    logging.info(
        "Partidas processadas: %s",
        total_matches,
    )

    logging.info(
        "Novas coletas: %s",
        counters["new"],
    )

    logging.info(
        "Arquivos existentes válidos: %s",
        counters["skipped"],
    )

    logging.info(
        "Não encontradas (HTTP 404): %s",
        counters["not_found"],
    )

    logging.info(
        "Falhas técnicas: %s",
        counters["failed"],
    )

    logging.info(
        "Diretório: %s",
        SAVE_PATH,
    )

    logging.info("=" * 60)


# =============================================================================
# PONTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    main()
