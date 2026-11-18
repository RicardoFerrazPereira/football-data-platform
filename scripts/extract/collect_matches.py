
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
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

# Aceita TEAM_ID via argumento ou utiliza o Vasco como padrão.
TEAM_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1974

# Arquivo consolidado de temporadas.
SEASONS_PATH = Path("data/raw/seasons/seasons.json")

# Diretórios de armazenamento.
RAW_PATH = Path("data/raw/matches/raw")
SAVE_PATH = Path("data/raw/matches")

RAW_PATH.mkdir(parents=True, exist_ok=True)
SAVE_PATH.mkdir(parents=True, exist_ok=True)

# Configurações do navegador.
HEADLESS = False
TIMEOUT = 60000

# Intervalos entre requisições.
SLEEP_BETWEEN_PAGES = 1
SLEEP_BETWEEN_SEASONS = 1

# Número máximo de tentativas por requisição.
MAX_RETRIES = 3

# Limite de segurança para evitar paginação infinita.
MAX_PAGES_PER_SEASON = 1000

logger.info(
    f"Coletando partidas — TEAM_ID referência: {TEAM_ID}"
)

class NonRetryableHTTPError(RuntimeError):
    """Erro HTTP que não deve gerar novas tentativas."""
    pass


# =====================================
# LOAD SEASONS
# =====================================

def load_seasons():
    """
    Carrega as temporadas consolidadas pelo collect_seasons.py.

    Valida a existência do arquivo, o formato da lista e os
    campos necessários para consultar as partidas.
    """

    if not SEASONS_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de seasons não encontrado: {SEASONS_PATH}\n"
            f"Execute primeiro: python collect_seasons.py {TEAM_ID}"
        )

    with open(SEASONS_PATH, "r", encoding="utf-8") as file:
        seasons = json.load(file)

    if not isinstance(seasons, list):
        raise ValueError(
            "O arquivo seasons.json não contém uma lista JSON."
        )

    if not seasons:
        raise ValueError(
            "O arquivo seasons.json está vazio. "
            "A coleta de partidas foi interrompida."
        )

    valid_seasons = []

    for season in seasons:

        if not isinstance(season, dict):
            logger.warning(
                "Registro de temporada inválido. Ignorando."
            )
            continue

        required_fields = [
            "tournament_id",
            "tournament_name",
            "season_id",
            "season_name",
        ]

        missing_fields = [
            field
            for field in required_fields
            if season.get(field) is None
        ]

        if missing_fields:
            logger.warning(
                f"Temporada ignorada por campos ausentes: "
                f"{missing_fields}"
            )
            continue

        valid_seasons.append(season)

    if not valid_seasons:
        raise ValueError(
            "Nenhuma temporada válida foi encontrada."
        )

    logger.info(
        f"Seasons carregadas: {len(valid_seasons)}"
    )

    return valid_seasons


# =====================================
# LOAD EXISTING MATCHES
# INCREMENTAL CONTROL
# =====================================

def load_existing_matches():
    """
    Carrega as partidas já armazenadas em matches.json.

    Utiliza match_id como identificador para evitar duplicações.

    Os registros existentes serão utilizados para:
    - Atualizar partidas encontradas novamente na API.
    - Preservar partidas de temporadas cuja coleta falhar.
    """

    matches_file = SAVE_PATH / "matches.json"

    if not matches_file.exists():
        logger.info(
            "Nenhuma partida existente — iniciando coleta do zero."
        )
        return {}

    with open(matches_file, "r", encoding="utf-8") as file:
        existing_data = json.load(file)

    if not isinstance(existing_data, list):
        raise ValueError(
            "O arquivo matches.json não contém uma lista JSON. "
            "Coleta interrompida para proteger os dados anteriores."
        )

    existing_matches = {}

    for match in existing_data:

        if not isinstance(match, dict):
            logger.warning(
                "Registro inválido encontrado em matches.json."
            )
            continue

        match_id = match.get("match_id")

        if match_id is None:
            logger.warning(
                "Partida sem match_id encontrada no arquivo existente."
            )
            continue

        existing_matches[match_id] = match

    logger.info(
        f"Partidas já existentes carregadas: "
        f"{len(existing_matches)}"
    )

    return existing_matches


# =====================================
# HELPERS
# =====================================

def parse_date(timestamp: int | float | None) -> str | None:
    """
    Converte Unix timestamp para data no padrão YYYY-MM-DD.

    A conversão utiliza UTC para manter consistência temporal
    com os dados coletados pela API.

    Retorna None quando o timestamp não está disponível.
    """

    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        ).strftime("%Y-%m-%d")

    except (ValueError, TypeError, OverflowError, OSError) as error:
        logger.warning(
            f"Timestamp inválido: {timestamp} — {error}"
        )
        return None


def save_json(data, file_path):
    """
    Salva um objeto JSON de maneira atômica.

    A gravação ocorre primeiro em um arquivo temporário.
    Após a conclusão, o arquivo definitivo é substituído.

    Isso evita deixar arquivos parcialmente escritos.
    """

    temp_file = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        temp_file.replace(file_path)

        logger.info(f"Arquivo salvo: {file_path}")

    except Exception:
        if temp_file.exists():
            temp_file.unlink()

        raise


# =====================================
# REQUEST WITH RETRY
# =====================================


def fetch_with_retry(page, url, max_retries=MAX_RETRIES):
    """
    Consulta um endpoint utilizando Playwright.

    Repete apenas falhas potencialmente temporárias.
    Interrompe imediatamente em erros HTTP não recuperáveis.
    """

    for attempt in range(max_retries):

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=TIMEOUT,
            )

            if response is None:
                raise RuntimeError(
                    "O navegador não recebeu uma resposta do endpoint."
                )

            status_code = response.status

            logger.info(f"STATUS HTTP: {status_code}")

            if status_code == 200:

                data = response.json()

                if not isinstance(data, dict):
                    raise ValueError(
                        "A resposta não possui estrutura JSON de objeto."
                    )

                return data

            if status_code in (403, 429):
                raise PermissionError(
                    f"HTTP {status_code}: acesso recusado ou "
                    "limite de requisições. Coleta interrompida."
                )

            if 400 <= status_code < 500:
                raise NonRetryableHTTPError(
                    f"Erro HTTP {status_code}. "
                    "Requisição não será repetida."
                )

            raise RuntimeError(
                f"Erro HTTP {status_code}"
            )

        except PermissionError:
            raise

        except NonRetryableHTTPError:
            raise

        except PlaywrightTimeoutError as error:

            logger.warning(
                f"TIMEOUT — tentativa {attempt + 1}/{max_retries}: "
                f"{error}"
            )

        except Exception as error:

            logger.warning(
                f"Falha na tentativa {attempt + 1}/{max_retries}: "
                f"{error}"
            )

        if attempt < max_retries - 1:

            wait_time = 2 ** attempt

            logger.info(
                f"Aguardando {wait_time}s antes de tentar novamente."
            )

            time.sleep(wait_time)

    logger.error(
        f"Falha após {max_retries} tentativas: {url}"
    )

    raise RuntimeError(
        f"Não foi possível consultar o endpoint: {url}"
    )


# =====================================
# NORMALIZE EVENT
# =====================================

def normalize_event(
    event: dict,
    tournament_id: int,
    tournament_name: str,
    season_id: int,
    season_name: str,
) -> dict:
    """
    Normaliza um evento da API para o formato padrão do projeto.

    Mantém os campos utilizados anteriormente:

    - match_id
    - match_date
    - status
    - slug
    - tournament_id
    - tournament_name
    - season_id
    - season_name
    - home_team_id
    - home_team_name
    - away_team_id
    - away_team_name
    - home_score
    - away_score
    - home_score_period1
    - away_score_period1
    - home_score_period2
    - away_score_period2
    - home_score_penalties
    - away_score_penalties
    - home_score_current
    - away_score_current
    """

    # Obtém os objetos internos com segurança.
    home_team = event.get("homeTeam") or {}
    away_team = event.get("awayTeam") or {}

    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}

    status_data = event.get("status") or {}

    # Garante que os objetos internos sejam dicionários.
    if not isinstance(home_team, dict):
        home_team = {}

    if not isinstance(away_team, dict):
        away_team = {}

    if not isinstance(home_score, dict):
        home_score = {}

    if not isinstance(away_score, dict):
        away_score = {}

    if not isinstance(status_data, dict):
        status_data = {}

    return {

        # =====================================
        # MATCH
        # =====================================

        "match_id": event.get("id"),

        "match_date": parse_date(
            event.get("startTimestamp")
        ),

        "status": status_data.get("type"),

        "slug": event.get("slug"),

        # =====================================
        # TOURNAMENT
        # =====================================

        "tournament_id": tournament_id,

        "tournament_name": tournament_name,

        "season_id": season_id,

        "season_name": season_name,

        # =====================================
        # HOME TEAM
        # =====================================

        "home_team_id": home_team.get("id"),

        "home_team_name": home_team.get("name"),

        # =====================================
        # AWAY TEAM
        # =====================================

        "away_team_id": away_team.get("id"),

        "away_team_name": away_team.get("name"),

        # =====================================
        # SCORE - NORMAL TIME
        # =====================================

        "home_score": home_score.get(
            "normaltime",
            home_score.get("display"),
        ),

        "away_score": away_score.get(
            "normaltime",
            away_score.get("display"),
        ),

        # =====================================
        # SCORE - FIRST HALF
        # =====================================

        "home_score_period1": home_score.get("period1"),

        "away_score_period1": away_score.get("period1"),

        # =====================================
        # SCORE - SECOND HALF
        # =====================================

        "home_score_period2": home_score.get("period2"),

        "away_score_period2": away_score.get("period2"),

        # =====================================
        # SCORE - PENALTIES
        # =====================================

        "home_score_penalties": home_score.get("penalties"),

        "away_score_penalties": away_score.get("penalties"),

        # =====================================
        # SCORE - SOFASCORE CURRENT
        # =====================================

        "home_score_current": home_score.get("current"),

        "away_score_current": away_score.get("current"),
    }


# =====================================
# COLLECT ONE SEASON
# =====================================

def collect_season(
    page,
    season,
):
    """
    Coleta todas as páginas de partidas de uma temporada.

    Utiliza o endpoint já existente no projeto:

    /unique-tournament/{tournament_id}/season/{season_id}/events/last/{page}

    A paginação continua enquanto hasNextPage indicar a existência
    de outra página.

    Diferentemente da versão anterior, não encerra a coleta
    simplesmente porque uma página não contém partidas novas.

    As partidas são armazenadas temporariamente durante a coleta.
    Somente após todas as páginas serem processadas com sucesso
    a temporada é considerada concluída.

    Se ocorrer uma falha no meio da paginação, os registros
    parciais não serão incorporados ao consolidado.
    """

    tournament_id = season["tournament_id"]
    season_id = season["season_id"]

    tournament_name = season["tournament_name"]
    season_name = season["season_name"]

    logger.info(
        f"Processando: {tournament_name} | {season_name}"
    )

    # Armazena as partidas da temporada atual.
    season_matches = {}

    page_number = 0

    while True:

        # Proteção contra paginação infinita.
        if page_number >= MAX_PAGES_PER_SEASON:
            raise RuntimeError(
                f"Limite de páginas atingido na temporada {season_id}."
            )

        # Monta o endpoint da página atual.
        url = (
            f"{BASE_URL}/unique-tournament/"
            f"{tournament_id}"
            f"/season/{season_id}"
            f"/events/last/{page_number}"
        )

        logger.info(
            f"Consultando página {page_number} — "
            f"{tournament_name} | {season_name}"
        )

        # Consulta a API com retry.
        data = fetch_with_retry(page, url)

        # Valida a estrutura dos eventos.
        events = data.get("events")

        if not isinstance(events, list):
            raise ValueError(
                f"Campo 'events' ausente ou inválido "
                f"na página {page_number} da temporada {season_id}."
            )

        logger.info(
            f"PAGE {page_number} | "
            f"Eventos recebidos: {len(events)}"
        )

        # =====================================
        # SAVE RAW PAGE
        # =====================================

        raw_file = (
            RAW_PATH
            / f"{tournament_id}_{season_id}_page_{page_number}.json"
        )

        save_json(data, raw_file)

        # =====================================
        # NORMALIZATION
        # =====================================

        for event in events:

            if not isinstance(event, dict):
                logger.warning(
                    "Evento inválido encontrado. Registro ignorado."
                )
                continue

            match_id = event.get("id")

            if match_id is None:
                logger.warning(
                    "Evento sem ID encontrado. Registro ignorado."
                )
                continue

            match = normalize_event(
                event=event,
                tournament_id=tournament_id,
                tournament_name=tournament_name,
                season_id=season_id,
                season_name=season_name,
            )

            # Utiliza match_id como chave para evitar duplicatas
            # entre páginas ou dentro da própria resposta.
            season_matches[match_id] = match

        logger.info(
            f"Partidas acumuladas na temporada: "
            f"{len(season_matches)}"
        )

        # =====================================
        # PAGINATION
        # =====================================

        has_next_page = data.get("hasNextPage")

        if not isinstance(has_next_page, bool):
            raise ValueError(
                f"Campo 'hasNextPage' ausente ou inválido "
                f"na página {page_number} da temporada {season_id}."
            )

        if not has_next_page:
            logger.info(
                f"Paginação concluída: {tournament_name} | {season_name}"
            )
            break

        page_number += 1

        time.sleep(SLEEP_BETWEEN_PAGES)

    logger.info(
        f"TOTAL DA TEMPORADA: {len(season_matches)} partidas"
    )

    return season_matches


# =====================================
# COLLECT ALL SEASONS
# =====================================

def collect_all_seasons(seasons):
    """
    Executa a coleta de partidas de todas as temporadas.

    O Chromium é inicializado uma única vez e a mesma página
    é reutilizada durante toda a execução.

    Cada temporada é processada individualmente.

    Uma falha em determinada temporada não impede a tentativa
    de coleta das demais.

    Retorna:
    - partidas coletadas com sucesso;
    - identificadores das temporadas concluídas;
    - identificadores das temporadas com falha.
    """

    collected_matches = {}

    successful_seasons = set()
    failed_seasons = set()

    total_seasons = len(seasons)

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=HEADLESS
        )

        try:
            context = browser.new_context()
            page = context.new_page()

            page.set_default_timeout(TIMEOUT)

            for index, season in enumerate(seasons, start=1):

                tournament_id = season["tournament_id"]
                season_id = season["season_id"]

                # A chave composta evita confusão caso IDs
                # de temporadas sejam associados a torneios diferentes.
                season_key = (tournament_id, season_id)

                logger.info("=" * 60)
                logger.info(
                    f"TEMPORADA {index}/{total_seasons}"
                )

                try:
                    # Coleta a temporada inteira.
                    season_matches = collect_season(
                        page=page,
                        season=season,
                    )

                    # Só incorpora os registros após o término
                    # bem-sucedido de toda a paginação.
                    collected_matches.update(season_matches)

                    successful_seasons.add(season_key)

                except PermissionError:
                    raise

                except Exception as error:

                    logger.error(
                        f"FALHA NA TEMPORADA "
                        f"{season.get('season_name')} "
                        f"(ID: {season_id}) — {error}"
                    )

                    failed_seasons.add(season_key)

                # Aguarda antes de processar a próxima temporada.
                if index < total_seasons:
                    time.sleep(SLEEP_BETWEEN_SEASONS)

        finally:
            browser.close()

    return (
        collected_matches,
        successful_seasons,
        failed_seasons,
    )


# =====================================
# MERGE EXISTING + NEW
# =====================================

def merge_matches(
    existing_matches,
    collected_matches,
    successful_seasons,
):
    """
    Consolida partidas novas com as partidas existentes.

    Regras:

    1. Temporadas coletadas com sucesso:
       os registros anteriores daquela temporada são substituídos
       pelos dados recém-coletados.

    2. Temporadas cuja coleta falhou:
       os registros anteriores são preservados.

    3. Partidas novas:
       são incorporadas ao consolidado.

    4. Partidas existentes sem identificação de temporada:
       são preservadas.

    A substituição dos registros encontrados permite atualizar
    status, placares, datas e demais informações da partida.
    """

    merged_matches = {}

    # Preserva os registros de temporadas que não foram
    # coletadas com sucesso nesta execução.
    for match_id, match in existing_matches.items():

        tournament_id = match.get("tournament_id")
        season_id = match.get("season_id")

        season_key = (tournament_id, season_id)

        # Registros sem identificação de temporada são preservados.
        if tournament_id is None or season_id is None:
            merged_matches[match_id] = match
            continue

        # Registros de temporadas com falha são preservados.
        if season_key not in successful_seasons:
            merged_matches[match_id] = match

    # Incorpora os dados recém-coletados das temporadas concluídas.
    merged_matches.update(collected_matches)

    logger.info(
        f"Partidas existentes: {len(existing_matches)}"
    )

    logger.info(
        f"Partidas coletadas nesta execução: "
        f"{len(collected_matches)}"
    )

    logger.info(
        f"Partidas preservadas de temporadas com falha: "
        f"{len(merged_matches) - len(collected_matches)}"
    )

    logger.info(
        f"Total consolidado: {len(merged_matches)}"
    )

    return merged_matches


# =====================================
# MAIN
# =====================================

def main():
    """
    Executa o processo completo de coleta de partidas:

    1. Carrega as temporadas.
    2. Carrega as partidas existentes.
    3. Inicializa o Chromium.
    4. Coleta todas as páginas de cada temporada.
    5. Normaliza os eventos.
    6. Atualiza partidas de temporadas coletadas com sucesso.
    7. Preserva partidas de temporadas cuja coleta falhou.
    8. Salva matches.json.
    """

    logger.info("=" * 60)
    logger.info(
        f"INICIANDO COLETA DE PARTIDAS — TEAM_ID: {TEAM_ID}"
    )
    logger.info("=" * 60)

    # 1. Carrega as temporadas.
    seasons = load_seasons()

    # 2. Carrega as partidas existentes.
    existing_matches = load_existing_matches()

    # 3. Coleta as partidas das temporadas.
    (
        collected_matches,
        successful_seasons,
        failed_seasons,
    ) = collect_all_seasons(seasons)

    # 4. Consolida os dados novos com os anteriores.
    all_matches = merge_matches(
        existing_matches=existing_matches,
        collected_matches=collected_matches,
        successful_seasons=successful_seasons,
    )

    clean_matches = list(all_matches.values())

    # 5. Salva o consolidado.
    matches_file = SAVE_PATH / "matches.json"

    save_json(
        clean_matches,
        matches_file,
    )

    # 6. Exibe o resumo da execução.
    logger.info("=" * 60)
    logger.info("COLETA DE PARTIDAS FINALIZADA")
    logger.info(f"TEAM_ID referência: {TEAM_ID}")
    logger.info(f"Temporadas processadas: {len(seasons)}")
    logger.info(f"Temporadas com sucesso: {len(successful_seasons)}")
    logger.info(f"Temporadas com falha: {len(failed_seasons)}")
    logger.info(f"Partidas coletadas: {len(collected_matches)}")
    logger.info(f"Partidas anteriores: {len(existing_matches)}")
    logger.info(f"Total consolidado: {len(clean_matches)}")

    if failed_seasons:
        logger.warning(
            f"TEMPORADAS COM FALHA: {sorted(failed_seasons)}"
        )

    logger.info(f"ARQUIVO FINAL: {matches_file}")
    logger.info("=" * 60)


# =====================================
# EXECUTION
# =====================================

if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        logger.critical(
            f"COLETA INTERROMPIDA: {error}"
        )

        raise SystemExit(1)
