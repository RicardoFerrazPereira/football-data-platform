
import json
import logging
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


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

# Diretório de armazenamento dos arquivos JSON.
RAW_PATH = Path("data/raw/tournaments")
RAW_PATH.mkdir(parents=True, exist_ok=True)

# Configurações do navegador.
HEADLESS = False
TIMEOUT = 60000


# =====================================
# REQUEST
# =====================================

def fetch_tournaments(team_id):
    """
    Acessa o endpoint de torneios do time utilizando Playwright.

    O navegador Chromium é utilizado para realizar a requisição,
    seguindo a mesma estratégia adotada no coletor de escalações.

    Retorna o JSON recebido quando a resposta é válida.
    """

    url = f"{BASE_URL}/team/{team_id}/unique-tournaments"

    logger.info(f"Consultando endpoint: {url}")

    try:
        with sync_playwright() as playwright:

            # Inicializa o navegador Chromium.
            browser = playwright.chromium.launch(
                headless=HEADLESS
            )

            try:
                # Cria um contexto e uma página para a requisição.
                context = browser.new_context()
                page = context.new_page()

                page.set_default_timeout(TIMEOUT)

                # Acessa diretamente o endpoint da API.
                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=TIMEOUT,
                )

                # Verifica se o navegador recebeu uma resposta.
                if response is None:
                    raise RuntimeError(
                        "O navegador não recebeu uma resposta do endpoint."
                    )

                status_code = response.status

                logger.info(f"STATUS CODE: {status_code}")

                # Interrompe a coleta quando a API retorna erro HTTP.
                if status_code != 200:
                    raise RuntimeError(
                        f"Erro na requisição — STATUS {status_code}"
                    )

                # Converte o conteúdo da resposta para JSON.
                data = response.json()

                # Valida a estrutura básica da resposta.
                if not isinstance(data, dict):
                    raise ValueError(
                        "A resposta recebida não possui estrutura JSON de objeto."
                    )

                if "uniqueTournaments" not in data:
                    raise ValueError(
                        "Campo 'uniqueTournaments' não encontrado na resposta."
                    )

                if not isinstance(data["uniqueTournaments"], list):
                    raise ValueError(
                        "O campo 'uniqueTournaments' não contém uma lista."
                    )

                return data

            finally:
                # Garante o fechamento do navegador mesmo em caso de erro.
                browser.close()

    except PlaywrightTimeoutError as error:
        logger.error(f"TIMEOUT durante a coleta: {error}")
        raise

    except Exception as error:
        logger.error(f"Erro durante a coleta dos torneios: {error}")
        raise


# =====================================
# SAVE JSON
# =====================================

def save_json(data, file_path):
    """
    Salva um objeto JSON em disco.

    A gravação é feita primeiro em um arquivo temporário.
    Somente depois de concluída a gravação o arquivo definitivo
    é substituído.

    Isso evita deixar arquivos parcialmente escritos em caso de falha.
    """

    temp_file = file_path.with_suffix(file_path.suffix + ".tmp")

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

        # Substitui o arquivo definitivo somente após salvar corretamente.
        temp_file.replace(file_path)

        logger.info(f"Arquivo salvo: {file_path}")

    except Exception:
        # Remove o temporário caso a gravação tenha falhado.
        if temp_file.exists():
            temp_file.unlink()

        raise


# =====================================
# NORMALIZATION
# =====================================

def normalize_tournaments(data):
    """
    Normaliza os torneios recebidos da API.

    Mantém os campos utilizados anteriormente pelo projeto:
    - tournament_id
    - tournament_name
    - tournament_slug
    - category
    - category_slug
    """

    unique_tournaments = data.get("uniqueTournaments", [])

    tournaments = []

    for tournament in unique_tournaments:

        # Ignora registros que não sejam objetos JSON.
        if not isinstance(tournament, dict):
            logger.warning(
                "Registro de torneio ignorado: formato inválido."
            )
            continue

        # Obtém os dados da categoria com segurança.
        category_data = tournament.get("category") or {}

        if not isinstance(category_data, dict):
            category_data = {}

        normalized_tournament = {
            "tournament_id": tournament.get("id"),
            "tournament_name": tournament.get("name"),
            "tournament_slug": tournament.get("slug"),
            "category": category_data.get("name"),
            "category_slug": category_data.get("slug"),
        }

        tournaments.append(normalized_tournament)

    logger.info(
        f"TORNEIOS NORMALIZADOS: {len(tournaments)}"
    )

    return tournaments


# =====================================
# REMOVE DUPLICATES
# =====================================

def remove_duplicates(tournaments):
    """
    Remove torneios duplicados utilizando tournament_id como chave.

    A ordem original dos registros é preservada.
    Registros sem identificador são descartados, pois não podem
    ser identificados com segurança para deduplicação.
    """

    clean_tournaments = {}
    invalid_records = 0

    for tournament in tournaments:

        tournament_id = tournament.get("tournament_id")

        if tournament_id is None:
            invalid_records += 1
            continue

        clean_tournaments[tournament_id] = tournament

    if invalid_records:
        logger.warning(
            f"REGISTROS SEM tournament_id DESCARTADOS: {invalid_records}"
        )

    result = list(clean_tournaments.values())

    logger.info(
        f"TORNEIOS APÓS DEDUPLICAÇÃO: {len(result)}"
    )

    return result


# =====================================
# MAIN
# =====================================

def main():
    """
    Executa o processo completo de coleta de torneios:

    1. Consulta a API utilizando Playwright.
    2. Valida a resposta recebida.
    3. Salva o JSON bruto.
    4. Normaliza os torneios.
    5. Remove registros duplicados.
    6. Salva o JSON normalizado.
    """

    logger.info("=" * 60)
    logger.info(f"INICIANDO COLETA DE TORNEIOS — TEAM_ID: {TEAM_ID}")
    logger.info("=" * 60)

    # Define os caminhos dos arquivos de saída.
    raw_file = RAW_PATH / f"team_{TEAM_ID}_tournaments_raw.json"
    clean_file = RAW_PATH / f"team_{TEAM_ID}_tournaments.json"

    # 1. Coleta os dados da API.
    data = fetch_tournaments(TEAM_ID)

    # 2. Salva a resposta original, sem alterações.
    save_json(data, raw_file)

    # 3. Normaliza os registros recebidos.
    tournaments = normalize_tournaments(data)

    # 4. Remove duplicatas.
    clean_tournaments = remove_duplicates(tournaments)

    # 5. Salva os dados normalizados.
    save_json(clean_tournaments, clean_file)

    # 6. Exibe o resumo da execução.
    logger.info("=" * 60)
    logger.info("COLETA DE TORNEIOS FINALIZADA")
    logger.info(f"TEAM_ID: {TEAM_ID}")
    logger.info(f"TOTAL TOURNAMENTS: {len(clean_tournaments)}")
    logger.info(f"RAW: {raw_file}")
    logger.info(f"CLEAN: {clean_file}")
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
