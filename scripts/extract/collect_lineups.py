# =============================================================================
# collect_lineups.py
# =============================================================================
# Coleta as escalações das partidas do SofaScore utilizando Playwright.
#
# Fluxo:
#
#   matches.parquet
#        ↓
#   filtro por ano
#        ↓
#   seleção opcional por --limit ou --match-id
#        ↓
#   consulta ao endpoint de escalações
#        ↓
#   JSON bruto em data/raw/lineups
#
# O processo é incremental:
# - escalações confirmadas com jogadores são ignoradas;
# - escalações provisórias são consultadas novamente;
# - arquivos sem jogadores permanecem como pendentes;
# - arquivos JSON são gravados atomicamente.
#
# Uso:
#
#   python .\scripts\extract\collect_lineups.py 2026
#
# Teste limitado:
#
#   python .\scripts\extract\collect_lineups.py 2026 --limit 5
#
# Teste de uma partida específica:
#
#   python .\scripts\extract\collect_lineups.py 2026 --match-id 15235414
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

# Endpoint utilizado para consultar as escalações.
BASE_URL = "https://www.sofascore.com/api/v1/event"

# Arquivo consolidado de partidas utilizado como entrada.
MATCHES_PATH = Path("data/processed/matches.parquet")

# Diretório onde os JSONs brutos de escalações serão armazenados.
SAVE_PATH = Path("data/raw/lineups")

# Ano utilizado quando nenhum ano é informado na linha de comando.
DEFAULT_FILTER_YEAR = 2026

# Tempo de espera entre requisições.
SLEEP_BETWEEN_REQUESTS = 2

# Número máximo de tentativas para erros que podem ser repetidos.
MAX_RETRIES = 3

# Timeout de navegação do Playwright em milissegundos.
NAVIGATION_TIMEOUT = 30_000

# Mantemos o navegador visível durante os testes.
# Pode ser alterado para True quando quisermos executar em modo headless.
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
    Representa um erro HTTP que deve interromper imediatamente a coleta.

    Exemplos:
    - HTTP 403
    - HTTP 429
    """

    pass


class NonRetryableHTTPError(Exception):
    """
    Representa um erro HTTP que não deve ser repetido.

    É utilizado para erros 4xx que não sejam tratados especificamente
    como fatais ou como HTTP 404.
    """

    pass


class CollectionError(Exception):
    """
    Representa um erro técnico ocorrido durante a coleta.

    Esses erros podem ser submetidos à política de retry.
    """

    pass


# =============================================================================
# ARGUMENTOS DA LINHA DE COMANDO
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    """
    Lê e valida os argumentos fornecidos pela linha de comando.

    Argumentos disponíveis:

    year:
        Ano das partidas que serão processadas.

    --limit:
        Limita a quantidade de partidas processadas.
        Útil para testes controlados.

    --match-id:
        Processa exclusivamente uma partida específica.
        Tem prioridade sobre --limit.
    """

    # -------------------------------------------------------------------------
    # Criação do parser principal.
    # -------------------------------------------------------------------------

    parser = argparse.ArgumentParser(
        description="Coleta escalações das partidas do SofaScore."
    )

    # -------------------------------------------------------------------------
    # Ano das partidas.
    # -------------------------------------------------------------------------

    parser.add_argument(
        "year",
        nargs="?",
        type=int,
        default=DEFAULT_FILTER_YEAR,
        help=(
            f"Ano das partidas a coletar. "
            f"Padrão: {DEFAULT_FILTER_YEAR}."
        ),
    )

    # -------------------------------------------------------------------------
    # Limite opcional para testes.
    # -------------------------------------------------------------------------

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Limita a quantidade de partidas processadas. "
            "Utilizado principalmente para testes."
        ),
    )

    # -------------------------------------------------------------------------
    # Match ID específico para testes individuais.
    # -------------------------------------------------------------------------

    parser.add_argument(
        "--match-id",
        type=int,
        default=None,
        help=(
            "Processa somente o Match ID informado. "
            "Tem prioridade sobre --limit."
        ),
    )

    # -------------------------------------------------------------------------
    # Retorna os argumentos já convertidos para seus respectivos tipos.
    # -------------------------------------------------------------------------

    return parser.parse_args()


# =============================================================================
# CARREGAMENTO DAS PARTIDAS
# =============================================================================

def load_matches(year: int) -> pd.DataFrame:
    """
    Carrega o arquivo de partidas e filtra pelo ano informado.

    Também valida os campos essenciais utilizados pelo coletor.
    """

    # -------------------------------------------------------------------------
    # Verifica se o arquivo de entrada existe.
    # -------------------------------------------------------------------------

    if not MATCHES_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de partidas não encontrado: {MATCHES_PATH}"
        )

    # -------------------------------------------------------------------------
    # Carrega o Parquet.
    # -------------------------------------------------------------------------

    df = pd.read_parquet(MATCHES_PATH)

    logging.info("Matches carregados: %s", len(df))

    # -------------------------------------------------------------------------
    # Valida a presença das colunas necessárias.
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Normaliza a coluna de data.
    #
    # O arquivo Parquet já possui datetime, mas a conversão com utc=True
    # garante comportamento consistente.
    # -------------------------------------------------------------------------

    df["match_date"] = pd.to_datetime(
        df["match_date"],
        utc=True,
        errors="coerce",
    )

    # -------------------------------------------------------------------------
    # Remove partidas sem data.
    # -------------------------------------------------------------------------

    df = df[df["match_date"].notna()].copy()

    # -------------------------------------------------------------------------
    # Filtra pelo ano solicitado.
    # -------------------------------------------------------------------------

    df = df[df["match_date"].dt.year == year].copy()

    # -------------------------------------------------------------------------
    # Remove Match IDs nulos.
    # -------------------------------------------------------------------------

    df = df[df["match_id"].notna()].copy()

    # -------------------------------------------------------------------------
    # Normaliza o tipo do Match ID.
    # -------------------------------------------------------------------------

    df["match_id"] = df["match_id"].astype("int64")

    # -------------------------------------------------------------------------
    # Remove possíveis duplicidades.
    # -------------------------------------------------------------------------

    df = df.drop_duplicates(
        subset=["match_id"],
        keep="first",
    )

    # -------------------------------------------------------------------------
    # Ordena cronologicamente.
    # -------------------------------------------------------------------------

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
# CONTAGEM DE JOGADORES
# =============================================================================

def count_players(data: dict[str, Any]) -> int:
    """
    Conta os jogadores presentes nas escalações mandante e visitante.

    São considerados:
    - players;
    - substitutes.

    A função aceita estruturas incompletas porque o SofaScore pode retornar
    escalações provisórias.
    """

    # -------------------------------------------------------------------------
    # Inicializa o contador.
    # -------------------------------------------------------------------------

    total_players = 0

    # -------------------------------------------------------------------------
    # Percorre os dois lados da partida.
    # -------------------------------------------------------------------------

    for side in ("home", "away"):

        team_data = data.get(side)

        # ---------------------------------------------------------------------
        # Ignora estruturas ausentes ou inválidas.
        # ---------------------------------------------------------------------

        if not isinstance(team_data, dict):
            continue

        # ---------------------------------------------------------------------
        # Conta jogadores titulares.
        # ---------------------------------------------------------------------

        players = team_data.get("players", [])

        if isinstance(players, list):
            total_players += len(players)

        # ---------------------------------------------------------------------
        # Conta reservas.
        # ---------------------------------------------------------------------

        substitutes = team_data.get("substitutes", [])

        if isinstance(substitutes, list):
            total_players += len(substitutes)

    return total_players


# =============================================================================
# VALIDAÇÃO ESTRUTURAL DO JSON
# =============================================================================

def is_valid_lineup_json(data: Any) -> bool:
    """
    Verifica se o conteúdo possui uma estrutura mínima válida de escalação.

    A função não exige jogadores.

    Isso é importante porque uma resposta válida do SofaScore pode representar
    uma escalação ainda não disponível ou ainda não confirmada.
    """

    # -------------------------------------------------------------------------
    # O JSON raiz precisa ser um objeto/dicionário.
    # -------------------------------------------------------------------------

    if not isinstance(data, dict):
        return False

    # -------------------------------------------------------------------------
    # Pelo menos um dos lados precisa existir.
    # -------------------------------------------------------------------------

    if "home" not in data and "away" not in data:
        return False

    # -------------------------------------------------------------------------
    # Quando presentes, home e away devem ser objetos.
    # -------------------------------------------------------------------------

    for side in ("home", "away"):

        if side in data and not isinstance(data[side], dict):
            return False

    return True


# =============================================================================
# CARREGAMENTO DE JSON EXISTENTE
# =============================================================================

def load_existing_json(
    output_file: Path,
) -> tuple[bool, dict[str, Any] | None]:
    """
    Tenta carregar um JSON de escalação existente.

    Retorna:
        (True, data)  -> arquivo existe e possui estrutura válida.
        (False, None) -> arquivo inexistente ou inválido.
    """

    # -------------------------------------------------------------------------
    # Verifica se o arquivo existe.
    # -------------------------------------------------------------------------

    if not output_file.exists():
        return False, None

    # -------------------------------------------------------------------------
    # Tenta ler e interpretar o JSON.
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Valida a estrutura mínima.
    # -------------------------------------------------------------------------

    if not is_valid_lineup_json(data):

        logging.warning(
            "Arquivo JSON com estrutura inválida: %s",
            output_file,
        )

        return False, None

    return True, data


# =============================================================================
# REQUISIÇÃO DE UMA ESCALAÇÃO
# =============================================================================

def fetch_lineup(
    page: Any,
    match_id: int,
) -> dict[str, Any] | None:
    """
    Consulta a escalação de uma partida.

    Retorna:
        dict -> resposta JSON válida.
        None -> HTTP 404, quando a escalação não existe.

    Levanta:
        FatalHTTPError para HTTP 403/429.
        NonRetryableHTTPError para outros 4xx.
        CollectionError para problemas técnicos.
    """

    # -------------------------------------------------------------------------
    # Monta a URL específica da partida.
    # -------------------------------------------------------------------------

    url = f"{BASE_URL}/{match_id}/lineups"

    try:

        # ---------------------------------------------------------------------
        # Navega até o endpoint utilizando o navegador.
        # ---------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Garante que houve resposta HTTP.
    # -------------------------------------------------------------------------

    if response is None:
        raise CollectionError(
            f"Nenhuma resposta HTTP para Match ID {match_id}"
        )

    status = response.status

    # -------------------------------------------------------------------------
    # HTTP 200: processa o JSON.
    # -------------------------------------------------------------------------

    if status == 200:

        try:

            data = response.json()

        except Exception as exc:

            raise CollectionError(
                f"Resposta não pôde ser convertida para JSON "
                f"(Match ID {match_id})"
            ) from exc

        # ---------------------------------------------------------------------
        # Valida a estrutura mínima da resposta.
        # ---------------------------------------------------------------------

        if not is_valid_lineup_json(data):

            raise CollectionError(
                f"JSON de escalação inválido "
                f"(Match ID {match_id})"
            )

        return data

    # -------------------------------------------------------------------------
    # HTTP 404: escalação não encontrada.
    # -------------------------------------------------------------------------

    if status == 404:

        return None

    # -------------------------------------------------------------------------
    # HTTP 403/429: erro fatal.
    #
    # Não continuamos tentando porque isso pode representar bloqueio,
    # limitação ou restrição de acesso.
    # -------------------------------------------------------------------------

    if status in (403, 429):

        raise FatalHTTPError(
            f"HTTP {status} para Match ID {match_id}"
        )

    # -------------------------------------------------------------------------
    # Outros erros 4xx não são repetidos.
    # -------------------------------------------------------------------------

    if 400 <= status < 500:

        raise NonRetryableHTTPError(
            f"HTTP {status} para Match ID {match_id}"
        )

    # -------------------------------------------------------------------------
    # Erros 5xx podem ser temporários.
    # -------------------------------------------------------------------------

    if 500 <= status < 600:

        raise CollectionError(
            f"HTTP {status} para Match ID {match_id}"
        )

    # -------------------------------------------------------------------------
    # Qualquer outro status inesperado também será tratado como erro técnico.
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
    Executa a consulta da escalação aplicando política de retry.

    Retorna:

        ("ok", data)
            Consulta realizada com sucesso.

        ("not_found", None)
            HTTP 404.

        ("error", None)
            Erro não recuperável para aquela partida.

    Erros 403/429 são propagados para interromper a execução.
    """

    # -------------------------------------------------------------------------
    # Executa até MAX_RETRIES tentativas.
    # -------------------------------------------------------------------------

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            data = fetch_lineup(
                page,
                match_id,
            )

            # -----------------------------------------------------------------
            # HTTP 404.
            # -----------------------------------------------------------------

            if data is None:
                return "not_found", None

            # -----------------------------------------------------------------
            # Sucesso.
            # -----------------------------------------------------------------

            return "ok", data

        except FatalHTTPError:
            # -----------------------------------------------------------------
            # Erros fatais não devem ser ocultados nem repetidos.
            # -----------------------------------------------------------------

            raise

        except NonRetryableHTTPError as exc:
            # -----------------------------------------------------------------
            # Erros 4xx não repetíveis.
            # -----------------------------------------------------------------

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

            # -----------------------------------------------------------------
            # Se ainda houver tentativas, aguarda antes de repetir.
            # -----------------------------------------------------------------

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

    Isso evita deixar um arquivo principal parcialmente gravado caso o
    processo seja interrompido durante a escrita.
    """

    # -------------------------------------------------------------------------
    # Garante que o diretório exista.
    # -------------------------------------------------------------------------

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------------------
    # Define o arquivo temporário.
    # -------------------------------------------------------------------------

    temp_file = output_file.with_suffix(
        output_file.suffix + ".tmp"
    )

    try:

        # ---------------------------------------------------------------------
        # Grava o JSON temporário.
        # ---------------------------------------------------------------------

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

        # ---------------------------------------------------------------------
        # Substitui o arquivo final pelo temporário.
        # ---------------------------------------------------------------------

        temp_file.replace(output_file)

    except Exception:

        # ---------------------------------------------------------------------
        # Remove o temporário caso algo tenha dado errado.
        # ---------------------------------------------------------------------

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
    Processa uma única partida.

    Regras:

    1. Escalação confirmada + jogadores:
       ignora a partida.

    2. Escalação existente, mas não confirmada:
       realiza nova coleta.

    3. Escalação existente sem jogadores:
       realiza nova coleta.

    4. Arquivo inexistente:
       realiza nova coleta.

    5. Resposta sem jogadores:
       mantém como pendente.

    Retorna uma categoria utilizada pelos contadores do processo principal.
    """

    # -------------------------------------------------------------------------
    # Define o caminho do JSON da partida.
    # -------------------------------------------------------------------------

    output_file = SAVE_PATH / f"{match_id}.json"

    # -------------------------------------------------------------------------
    # Tenta carregar o arquivo existente.
    # -------------------------------------------------------------------------

    file_exists, existing_data = load_existing_json(
        output_file
    )

    # -------------------------------------------------------------------------
    # Se existe um JSON válido, verifica o estado atual da escalação.
    # -------------------------------------------------------------------------

    if file_exists and existing_data is not None:

        player_count = count_players(existing_data)

        confirmed = existing_data.get(
            "confirmed",
            False,
        )

        # ---------------------------------------------------------------------
        # Escalação confirmada e com jogadores:
        # não precisamos consultar novamente.
        # ---------------------------------------------------------------------

        if confirmed and player_count > 0:

            logging.info(
                "Escalação confirmada existente — pulando | "
                "Jogadores: %s",
                player_count,
            )

            return "skipped"

        # ---------------------------------------------------------------------
        # Escalação existente, mas provisória ou sem jogadores.
        # ---------------------------------------------------------------------

        logging.info(
            "Escalação provisória existente — refazendo coleta | "
            "Jogadores atuais: %s",
            player_count,
        )

    else:

        # ---------------------------------------------------------------------
        # Não existe arquivo válido.
        # ---------------------------------------------------------------------

        logging.info(
            "Escalação inexistente ou inválida — realizando nova coleta."
        )

    # -------------------------------------------------------------------------
    # Consulta a escalação atualizada.
    # -------------------------------------------------------------------------

    status, data = fetch_with_retry(
        page,
        match_id,
    )

    # -------------------------------------------------------------------------
    # HTTP 404.
    # -------------------------------------------------------------------------

    if status == "not_found":

        logging.warning(
            "Escalação não encontrada (HTTP 404)."
        )

        return "not_found"

    # -------------------------------------------------------------------------
    # Falha técnica.
    # -------------------------------------------------------------------------

    if status == "error" or data is None:

        logging.error(
            "Falha técnica na coleta."
        )

        return "failed"

    # -------------------------------------------------------------------------
    # Conta os jogadores retornados.
    # -------------------------------------------------------------------------

    player_count = count_players(data)

    # -------------------------------------------------------------------------
    # Verifica se a resposta está confirmada.
    # -------------------------------------------------------------------------

    confirmed = data.get(
        "confirmed",
        False,
    )

    # -------------------------------------------------------------------------
    # Se não houver jogadores, mantemos a resposta como pendente.
    # -------------------------------------------------------------------------

    if player_count == 0:

        # ---------------------------------------------------------------------
        # Se já existia um arquivo válido com jogadores, preservamos o
        # conteúdo anterior para evitar substituí-lo por uma resposta vazia.
        # ---------------------------------------------------------------------

        if file_exists and existing_data is not None:

            existing_player_count = count_players(
                existing_data
            )

            if existing_player_count > 0:

                logging.warning(
                    "Nova resposta sem jogadores. "
                    "Arquivo anterior preservado | "
                    "Jogadores anteriores: %s",
                    existing_player_count,
                )

                return "pending"

        # ---------------------------------------------------------------------
        # Não havia dados anteriores úteis.
        # Salva a resposta como pendente.
        # ---------------------------------------------------------------------

        save_json_atomic(
            data,
            output_file,
        )

        logging.warning(
            "Escalação salva como pendente — sem jogadores."
        )

        return "pending"

    # -------------------------------------------------------------------------
    # Há jogadores. Salva a resposta.
    # -------------------------------------------------------------------------

    save_json_atomic(
        data,
        output_file,
    )

    # -------------------------------------------------------------------------
    # Diferencia nova coleta de atualização.
    # -------------------------------------------------------------------------

    if file_exists:

        logging.info(
            "Escalação atualizada | Jogadores: %s | Confirmada: %s",
            player_count,
            confirmed,
        )

        return "updated"

    logging.info(
        "Nova escalação coletada | Jogadores: %s | Confirmada: %s",
        player_count,
        confirmed,
    )

    return "new"


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def main() -> None:
    """
    Executa o processo completo de coleta de escalações.
    """

    # -------------------------------------------------------------------------
    # Lê os argumentos da linha de comando.
    # -------------------------------------------------------------------------

    args = parse_arguments()

    # -------------------------------------------------------------------------
    # Garante que o diretório de saída exista.
    # -------------------------------------------------------------------------

    SAVE_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------------------
    # Cabeçalho da execução.
    # -------------------------------------------------------------------------

    logging.info("=" * 60)
    logging.info("COLETA DE ESCALAÇÕES")
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
    # Carrega as partidas do ano solicitado.
    # -------------------------------------------------------------------------

    matches = load_matches(
        args.year
    )

    # -------------------------------------------------------------------------
    # Seleção especial por Match ID.
    #
    # --match-id tem prioridade sobre --limit.
    # -------------------------------------------------------------------------

    if args.match_id is not None:

        matches = matches[
            matches["match_id"] == args.match_id
        ].copy()

        # ---------------------------------------------------------------------
        # Se o Match ID não pertence ao ano selecionado, interrompe.
        # ---------------------------------------------------------------------

        if matches.empty:

            raise ValueError(
                f"Match ID {args.match_id} não encontrado "
                f"entre as partidas de {args.year}."
            )

        logging.info(
            "Modo de teste: match-id=%s | "
            "Partida selecionada: 1",
            args.match_id,
        )

    # -------------------------------------------------------------------------
    # Caso não tenha sido informado Match ID, verifica --limit.
    # -------------------------------------------------------------------------

    elif args.limit is not None:

        # ---------------------------------------------------------------------
        # Valida o limite.
        # ---------------------------------------------------------------------

        if args.limit <= 0:

            raise ValueError(
                "--limit deve ser maior que zero."
            )

        # ---------------------------------------------------------------------
        # Seleciona somente as primeiras partidas.
        # ---------------------------------------------------------------------

        available_matches = len(matches)

        matches = matches.head(
            args.limit
        ).copy()

        logging.info(
            "Modo de teste: limit=%s | "
            "Partidas disponíveis=%s | "
            "Partidas processadas=%s",
            args.limit,
            available_matches,
            len(matches),
        )

    # -------------------------------------------------------------------------
    # Execução normal.
    # -------------------------------------------------------------------------

    else:

        logging.info(
            "Modo normal | Partidas a processar: %s",
            len(matches),
        )

    # -------------------------------------------------------------------------
    # Inicializa os contadores.
    # -------------------------------------------------------------------------

    counters = {
        "new": 0,
        "updated": 0,
        "skipped": 0,
        "pending": 0,
        "not_found": 0,
        "failed": 0,
    }

    # -------------------------------------------------------------------------
    # Inicializa Playwright.
    # -------------------------------------------------------------------------

    with sync_playwright() as playwright:

        browser = None
        context = None
        page = None

        try:

            # -----------------------------------------------------------------
            # Abre o Chromium.
            # -----------------------------------------------------------------

            browser = playwright.chromium.launch(
                headless=HEADLESS
            )

            # -----------------------------------------------------------------
            # Cria contexto do navegador.
            # -----------------------------------------------------------------

            context = browser.new_context(
                locale="pt-BR"
            )

            # -----------------------------------------------------------------
            # Cria página para as requisições.
            # -----------------------------------------------------------------

            page = context.new_page()

            # -----------------------------------------------------------------
            # Define timeout padrão.
            # -----------------------------------------------------------------

            page.set_default_timeout(
                NAVIGATION_TIMEOUT
            )

            # -----------------------------------------------------------------
            # Percorre as partidas selecionadas.
            # -----------------------------------------------------------------

            total_matches = len(matches)

            for index, row in matches.iterrows():

                match_id = int(
                    row["match_id"]
                )

                logging.info(
                    "[%s/%s] Match ID: %s",
                    index + 1,
                    total_matches,
                    match_id,
                )

                try:

                    # ---------------------------------------------------------
                    # Processa a partida.
                    # ---------------------------------------------------------

                    result = process_match(
                        page,
                        match_id,
                    )

                    # ---------------------------------------------------------
                    # Atualiza o contador correspondente.
                    # ---------------------------------------------------------

                    counters[result] += 1

                except FatalHTTPError:

                    # ---------------------------------------------------------
                    # Erros fatais interrompem imediatamente a execução.
                    # ---------------------------------------------------------

                    logging.critical(
                        "Erro fatal encontrado. "
                        "Coleta interrompida."
                    )

                    raise

                except Exception as exc:

                    # ---------------------------------------------------------
                    # Erros inesperados são registrados como falhas técnicas.
                    # ---------------------------------------------------------

                    logging.exception(
                        "Erro inesperado no Match ID %s: %s",
                        match_id,
                        exc,
                    )

                    counters["failed"] += 1

                # -------------------------------------------------------------
                # Aguarda entre requisições.
                #
                # Não é necessário aguardar após a última partida.
                # -------------------------------------------------------------

                if index < total_matches - 1:

                    page.wait_for_timeout(
                        SLEEP_BETWEEN_REQUESTS * 1000
                    )

        finally:

            # -----------------------------------------------------------------
            # Fecha a página.
            # -----------------------------------------------------------------

            if page is not None:
                page.close()

            # -----------------------------------------------------------------
            # Fecha o contexto.
            # -----------------------------------------------------------------

            if context is not None:
                context.close()

            # -----------------------------------------------------------------
            # Fecha o navegador.
            # -----------------------------------------------------------------

            if browser is not None:
                browser.close()

    # -------------------------------------------------------------------------
    # Relatório final.
    # -------------------------------------------------------------------------

    logging.info("")
    logging.info("=" * 60)
    logging.info("COLETA DE ESCALAÇÕES FINALIZADA")
    logging.info("=" * 60)

    logging.info(
        "Ano: %s",
        args.year,
    )

    logging.info(
        "Partidas processadas: %s",
        len(matches),
    )

    logging.info(
        "Novas coletas: %s",
        counters["new"],
    )

    logging.info(
        "Atualizadas: %s",
        counters["updated"],
    )

    logging.info(
        "Ignoradas (escalação confirmada): %s",
        counters["skipped"],
    )

    logging.info(
        "Pendentes sem jogadores: %s",
        counters["pending"],
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