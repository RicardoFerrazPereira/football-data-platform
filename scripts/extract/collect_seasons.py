
import json
import logging
import sys
import time
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

# Arquivo de torneios produzido pelo coletor anterior.
TOURNAMENTS_PATH = Path(
    f"data/raw/tournaments/team_{TEAM_ID}_tournaments.json"
)

# Diretórios de armazenamento.
RAW_PATH = Path("data/raw/seasons/raw")
SAVE_PATH = Path("data/raw/seasons")

RAW_PATH.mkdir(parents=True, exist_ok=True)
SAVE_PATH.mkdir(parents=True, exist_ok=True)

# Configurações do navegador.
HEADLESS = False
TIMEOUT = 60000

# Intervalo entre as requisições.
SLEEP_BETWEEN_REQUESTS = 1

logger.info(f"Coletando seasons para TEAM_ID: {TEAM_ID}")


# =====================================
# LOAD TOURNAMENTS
# =====================================

def load_tournaments():
    """
    Carrega a lista de torneios normalizados.

    O arquivo é produzido pelo collect_tournaments.py.
    A função valida sua existência e sua estrutura antes
    de iniciar qualquer requisição.
    """

    if not TOURNAMENTS_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de torneios não encontrado: {TOURNAMENTS_PATH}\n"
            f"Execute primeiro: python collect_tournaments.py {TEAM_ID}"
        )

    with open(TOURNAMENTS_PATH, "r", encoding="utf-8") as file:
        tournaments = json.load(file)

    if not isinstance(tournaments, list):
        raise ValueError(
            "O arquivo de torneios não contém uma lista JSON."
        )

    if not tournaments:
        raise ValueError(
            "O arquivo de torneios está vazio. "
            "A coleta de temporadas foi interrompida."
        )

    # Verifica se os registros possuem os campos necessários.
    valid_tournaments = []

    for tournament in tournaments:

        if not isinstance(tournament, dict):
            logger.warning("Registro de torneio inválido. Ignorando.")
            continue

        tournament_id = tournament.get("tournament_id")
        tournament_name = tournament.get("tournament_name")

        if tournament_id is None or not tournament_name:
            logger.warning(
                f"Torneio sem ID ou nome. Registro ignorado: {tournament}"
            )
            continue

        valid_tournaments.append(tournament)

    if not valid_tournaments:
        raise ValueError(
            "Nenhum torneio válido foi encontrado no arquivo."
        )

    logger.info(
        f"Torneios carregados: {len(valid_tournaments)}"
    )

    return valid_tournaments


# =====================================
# LOAD EXISTING SEASONS
# =====================================

def load_existing_seasons():
    """
    Carrega as temporadas consolidadas de uma execução anterior.

    Esses dados serão utilizados para preservar as temporadas
    dos torneios cuja coleta falhar nesta execução.

    Se o arquivo não existir, inicia com uma lista vazia.
    Se existir, mas estiver inválido, interrompe o processo
    para evitar sobrescrever dados que não puderam ser lidos.
    """

    save_file = SAVE_PATH / "seasons.json"

    if not save_file.exists():
        logger.info(
            "Arquivo consolidado anterior não encontrado. "
            "Será criado um novo."
        )
        return []

    with open(save_file, "r", encoding="utf-8") as file:
        existing_seasons = json.load(file)

    if not isinstance(existing_seasons, list):
        raise ValueError(
            "O arquivo seasons.json existente não contém uma lista JSON. "
            "A coleta foi interrompida para proteger os dados anteriores."
        )

    logger.info(
        f"Temporadas existentes carregadas: {len(existing_seasons)}"
    )

    return existing_seasons


# =====================================
# REQUEST
# =====================================

def fetch_seasons(page, tournament_id, tournament_name):
    """
    Consulta as temporadas de um torneio utilizando Playwright.

    Recebe uma página já aberta do Chromium, permitindo reutilizar
    o mesmo navegador durante toda a coleta.

    Retorna o JSON recebido quando a resposta é válida.

    Em caso de erro HTTP, timeout ou estrutura inválida,
    propaga a exceção para que o torneio seja contabilizado
    como uma coleta malsucedida.
    """

    url = (
        f"{BASE_URL}/unique-tournament/"
        f"{tournament_id}/seasons"
    )

    logger.info(
        f"Consultando seasons: {tournament_name} "
        f"(ID: {tournament_id})"
    )

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

        logger.info(f"STATUS: {status_code}")

        if status_code in (403, 429):
            raise PermissionError(
                f"HTTP {status_code}: acesso recusado ou limite "
                f"de requisições para o torneio {tournament_name}. "
                "Coleta interrompida."
            )

        if status_code != 200:
            raise RuntimeError(
                f"Erro HTTP {status_code} ao consultar "
                f"o torneio {tournament_name}."
            )

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError(
                "A resposta recebida não possui estrutura JSON de objeto."
            )

        if "seasons" not in data:
            raise ValueError(
                "Campo 'seasons' não encontrado na resposta."
            )

        if not isinstance(data["seasons"], list):
            raise ValueError(
                "O campo 'seasons' não contém uma lista."
            )

        return data

    except PlaywrightTimeoutError as error:
        logger.error(
            f"TIMEOUT no torneio {tournament_name}: {error}"
        )
        raise

    except Exception as error:
        logger.error(
            f"Falha ao consultar {tournament_name}: {error}"
        )
        raise


# =====================================
# SAVE JSON
# =====================================

def save_json(data, file_path):
    """
    Salva os dados JSON de maneira atômica.

    Primeiro grava o conteúdo em um arquivo temporário.
    Após a gravação bem-sucedida, substitui o arquivo definitivo.

    Assim, uma interrupção durante a gravação não deixa
    o arquivo definitivo parcialmente escrito.
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
# NORMALIZATION
# =====================================

def normalize_seasons(data, tournament_id, tournament_name):
    """
    Normaliza as temporadas retornadas pela API.

    Mantém os campos utilizados anteriormente pelo projeto:

    - season_id
    - season_name
    - year
    - tournament_id
    - tournament_name

    O ID e o nome do torneio são adicionados a cada temporada
    para permitir relacionamentos posteriores no DuckDB.
    """

    seasons_data = data.get("seasons", [])

    normalized_seasons = []

    for season in seasons_data:

        if not isinstance(season, dict):
            logger.warning(
                f"Temporada inválida no torneio {tournament_id}. "
                "Registro ignorado."
            )
            continue

        season_id = season.get("id")

        if season_id is None:
            logger.warning(
                f"Temporada sem ID no torneio {tournament_id}. "
                "Registro ignorado."
            )
            continue

        normalized_seasons.append(
            {
                "season_id": season_id,
                "season_name": season.get("name"),
                "year": season.get("year"),
                "tournament_id": tournament_id,
                "tournament_name": tournament_name,
            }
        )

    logger.info(
        f"Seasons encontradas: {len(normalized_seasons)}"
    )

    return normalized_seasons


# =====================================
# REMOVE DUPLICATES
# =====================================

def remove_duplicates(seasons):
    """
    Remove temporadas duplicadas utilizando season_id como chave.

    A ordem original dos registros é preservada.
    Caso um ID apareça mais de uma vez, prevalece o último registro.
    """

    clean_seasons = {}

    for season in seasons:

        season_id = season.get("season_id")

        if season_id is None:
            continue

        clean_seasons[season_id] = season

    result = list(clean_seasons.values())

    logger.info(
        f"TOTAL APÓS DEDUPLICAÇÃO: {len(result)}"
    )

    return result


# =====================================
# MERGE EXISTING AND NEW SEASONS
# =====================================

def merge_seasons(
    existing_seasons,
    collected_seasons,
    successful_tournament_ids,
):
    """
    Consolida temporadas novas com os dados anteriores.

    Regras:

    1. Torneios coletados com sucesso:
       utiliza os dados recém-coletados, substituindo os registros
       anteriores daquele torneio.

    2. Torneios cuja coleta falhou:
       preserva os registros existentes.

    3. Registros antigos sem tournament_id:
       preserva para evitar perda de dados não identificados.

    Uma resposta válida com lista vazia também é considerada
    sucesso: nesse caso, as temporadas anteriores daquele torneio
    não são mantidas.
    """

    successful_ids = set(successful_tournament_ids)

    preserved_seasons = []

    for season in existing_seasons:

        if not isinstance(season, dict):
            logger.warning(
                "Registro antigo inválido encontrado. "
                "Preservando o registro."
            )
            preserved_seasons.append(season)
            continue

        tournament_id = season.get("tournament_id")

        # Mantém temporadas de torneios que falharam.
        # Também preserva registros sem identificação do torneio.
        if (
            tournament_id is None
            or tournament_id not in successful_ids
        ):
            preserved_seasons.append(season)

    # Junta os dados preservados com os dados recém-coletados.
    merged_seasons = preserved_seasons + collected_seasons

    # Remove possíveis duplicatas pelo identificador da temporada.
    clean_seasons = remove_duplicates(merged_seasons)

    logger.info(
        f"Temporadas preservadas: {len(preserved_seasons)}"
    )

    logger.info(
        f"Temporadas novas coletadas: {len(collected_seasons)}"
    )

    logger.info(
        f"Total consolidado: {len(clean_seasons)}"
    )

    return clean_seasons


# =====================================
# COLLECT SEASONS
# =====================================

def collect_all_seasons(tournaments):
    """
    Executa a coleta de temporadas de todos os torneios.

    O Chromium é inicializado uma única vez e sua página
    é reutilizada durante as requisições.

    Cada torneio é processado individualmente. Uma falha em
    determinado torneio não impede a tentativa de coleta dos demais.

    Retorna:
    - temporadas coletadas;
    - IDs dos torneios coletados com sucesso;
    - IDs dos torneios cuja coleta falhou;
    - contadores da execução.
    """

    all_seasons = []

    successful_tournament_ids = []
    failed_tournament_ids = []

    total_tournaments = len(tournaments)

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=HEADLESS
        )

        try:
            context = browser.new_context()
            page = context.new_page()

            page.set_default_timeout(TIMEOUT)

            for index, tournament in enumerate(tournaments, start=1):

                tournament_id = tournament["tournament_id"]
                tournament_name = tournament["tournament_name"]

                logger.info("-" * 60)
                logger.info(
                    f"TORNEIO {index}/{total_tournaments}"
                )

                try:
                    # Consulta a API.
                    data = fetch_seasons(
                        page,
                        tournament_id,
                        tournament_name,
                    )

                    # Salva a resposta original do torneio.
                    raw_file = (
                        RAW_PATH
                        / f"tournament_{tournament_id}_seasons_raw.json"
                    )

                    save_json(data, raw_file)

                    # Normaliza as temporadas.
                    seasons = normalize_seasons(
                        data,
                        tournament_id,
                        tournament_name,
                    )

                    all_seasons.extend(seasons)

                    # Marca o torneio como coletado com sucesso.
                    successful_tournament_ids.append(
                        tournament_id
                    )

                except PermissionError:
                    raise

                except Exception as error:

                    logger.error(
                        f"COLETA FALHOU: {tournament_name} "
                        f"(ID: {tournament_id}) — {error}"
                    )

                    failed_tournament_ids.append(
                        tournament_id
                    )

                # Aguarda antes de consultar o próximo torneio.
                if index < total_tournaments:
                    time.sleep(SLEEP_BETWEEN_REQUESTS)

        finally:
            browser.close()

    return (
        all_seasons,
        successful_tournament_ids,
        failed_tournament_ids,
    )


# =====================================
# MAIN
# =====================================

def main():
    """
    Executa o processo completo de coleta de temporadas:

    1. Carrega os torneios.
    2. Carrega temporadas de execuções anteriores.
    3. Consulta a API utilizando Playwright.
    4. Salva os JSONs brutos por torneio.
    5. Normaliza as temporadas.
    6. Preserva dados de torneios cuja coleta falhou.
    7. Consolida e deduplica os registros.
    8. Salva seasons.json.
    """

    logger.info("=" * 60)
    logger.info(
        f"INICIANDO COLETA DE SEASONS — TEAM_ID: {TEAM_ID}"
    )
    logger.info("=" * 60)

    # 1. Carrega a lista de torneios.
    tournaments = load_tournaments()

    # 2. Carrega os dados consolidados anteriores.
    existing_seasons = load_existing_seasons()

    # 3. Coleta as temporadas dos torneios.
    (
        collected_seasons,
        successful_tournament_ids,
        failed_tournament_ids,
    ) = collect_all_seasons(tournaments)

    # 4. Consolida os dados novos com os anteriores.
    clean_seasons = merge_seasons(
        existing_seasons,
        collected_seasons,
        successful_tournament_ids,
    )

    # 5. Salva o arquivo consolidado.
    save_file = SAVE_PATH / "seasons.json"

    save_json(clean_seasons, save_file)

    # 6. Exibe o resumo da execução.
    logger.info("=" * 60)
    logger.info("COLETA DE SEASONS FINALIZADA")
    logger.info(f"TEAM_ID: {TEAM_ID}")
    logger.info(
        f"TORNEIOS PROCESSADOS: {len(tournaments)}"
    )
    logger.info(
        f"TORNEIOS COM SUCESSO: {len(successful_tournament_ids)}"
    )
    logger.info(
        f"TORNEIOS COM FALHA: {len(failed_tournament_ids)}"
    )
    logger.info(
        f"TOTAL SEASONS COLETADAS: {len(collected_seasons)}"
    )
    logger.info(
        f"TOTAL SEASONS CONSOLIDADAS: {len(clean_seasons)}"
    )

    if failed_tournament_ids:
        logger.warning(
            f"IDs DOS TORNEIOS COM FALHA: {failed_tournament_ids}"
        )

    logger.info(f"ARQUIVO FINAL: {save_file}")
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
