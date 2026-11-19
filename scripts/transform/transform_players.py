import json
import logging
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "lineups"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "players.parquet"
TEMP_FILE = OUTPUT_FILE.with_name("players.tmp.parquet")

SIDES = ["home", "away"]

OUTPUT_COLUMNS = [
    "player_id",
    "player_name",
    "short_name",
    "slug",
    "position",
    "height",
    "preferred_foot",
    "country_name",
    "country_alpha2",
    "birth_date",
]

COMPLETENESS_COLUMNS = [
    "player_name",
    "short_name",
    "slug",
    "position",
    "height",
    "preferred_foot",
    "country_name",
    "country_alpha2",
    "birth_timestamp",
]


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
# FUNÇÕES AUXILIARES
# ============================================================

def to_int(value):
    """Converte um valor para inteiro, retornando None se inválido."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None

        return int(value)

    except (TypeError, ValueError, OverflowError):
        return None


def load_json_file(file_path):
    """Carrega e valida a estrutura básica de um JSON."""

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("A raiz do JSON não é um objeto.")

    return data


# ============================================================
# EXTRAÇÃO
# ============================================================

def extract_players(data, file_name):
    """Extrai os jogadores dos lados home e away."""

    match_players = []

    for side in SIDES:
        side_data = data.get(side)

        if not isinstance(side_data, dict):
            continue

        players = side_data.get("players", [])

        if not isinstance(players, list):
            continue

        for item in players:
            if not isinstance(item, dict):
                continue

            player = item.get("player")

            if not isinstance(player, dict):
                continue

            player_id = to_int(player.get("id"))

            if player_id is None:
                continue

            country = player.get("country")

            if not isinstance(country, dict):
                country = {}

            match_players.append({
                "player_id": player_id,
                "player_name": player.get("name"),
                "short_name": player.get("shortName"),
                "slug": player.get("slug"),
                "position": player.get("position"),
                "height": to_int(player.get("height")),
                "preferred_foot": player.get("preferredFoot"),
                "country_name": country.get("name"),
                "country_alpha2": country.get("alpha2"),
                "birth_timestamp": to_int(
                    player.get("dateOfBirthTimestamp")
                ),
            })

    return match_players


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_players(df):
    """Mantém uma ocorrência por jogador, priorizando registros completos."""

    if df.empty:
        return df

    df = df.copy()

    df["_completeness"] = (
        df[COMPLETENESS_COLUMNS]
        .notna()
        .sum(axis=1)
    )

    df = df.sort_values(
        by="_completeness",
        ascending=False,
        kind="stable",
    )

    duplicated_count = df.duplicated(
        subset=["player_id"]
    ).sum()

    logger.info(
        "Registros duplicados encontrados: %s",
        duplicated_count,
    )

    df = df.drop_duplicates(
        subset=["player_id"],
        keep="first",
    )

    return df.drop(columns=["_completeness"])


# ============================================================
# TRANSFORMAÇÃO
# ============================================================

def transform_dataframe(players):
    """Converte os registros extraídos para o formato final."""

    df = pd.DataFrame(players)

    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df["birth_date"] = pd.to_datetime(
        df["birth_timestamp"],
        unit="s",
        utc=True,
        errors="coerce",
    ).dt.tz_localize(None)

    df = deduplicate_players(df)

    df["height"] = df["height"].astype("Int64")

    df = df.drop(columns=["birth_timestamp"])

    df = df[OUTPUT_COLUMNS]

    df = df.sort_values(
        by="player_name",
        na_position="last",
    ).reset_index(drop=True)

    return df


# ============================================================
# VALIDAÇÃO
# ============================================================

def validate_dataframe(df):
    """Valida a estrutura e a integridade dos dados transformados."""

    if list(df.columns) != OUTPUT_COLUMNS:
        raise ValueError(
            "O schema do DataFrame não corresponde ao esperado."
        )

    if df["player_id"].isna().any():
        raise ValueError("Existem player_id nulos.")

    if df["player_id"].duplicated().any():
        raise ValueError("Existem player_id duplicados.")

    if not pd.api.types.is_integer_dtype(df["player_id"]):
        raise ValueError("player_id não possui tipo inteiro.")

    if "jersey_number" in df.columns:
        raise ValueError(
            "A coluna jersey_number não deve existir em players.parquet."
        )


# ============================================================
# GRAVAÇÃO
# ============================================================

def save_parquet(df):
    """Grava o Parquet temporariamente, valida e substitui o destino."""

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        df.to_parquet(
            TEMP_FILE,
            engine="pyarrow",
            compression="snappy",
            index=False,
        )

        # Confere o arquivo efetivamente gravado.
        check_df = pd.read_parquet(TEMP_FILE)

        validate_dataframe(check_df)

        if len(check_df) != len(df):
            raise ValueError(
                "A quantidade de registros mudou após a gravação."
            )

        TEMP_FILE.replace(OUTPUT_FILE)

    except Exception:
        if TEMP_FILE.exists():
            TEMP_FILE.unlink()

        raise


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():

    logger.info("Iniciando transformação dos jogadores.")

    if not INPUT_DIR.exists():
        raise FileNotFoundError(
            f"Diretório de entrada não encontrado: {INPUT_DIR}"
        )

    json_files = sorted(INPUT_DIR.glob("*.json"))

    logger.info("Arquivos encontrados: %s", len(json_files))

    all_players = []

    processed_files = 0
    invalid_files = 0
    empty_files = 0

    for file_path in json_files:

        try:
            data = load_json_file(file_path)

            players = extract_players(
                data,
                file_path.name,
            )

            if players:
                all_players.extend(players)
                processed_files += 1
            else:
                empty_files += 1

        except (json.JSONDecodeError, OSError, ValueError) as error:
            invalid_files += 1

            logger.warning(
                "Arquivo inválido %s: %s",
                file_path.name,
                error,
            )

    logger.info("Arquivos processados: %s", processed_files)
    logger.info("Arquivos inválidos: %s", invalid_files)
    logger.info("Arquivos sem jogadores válidos: %s", empty_files)

    logger.info(
        "Total de registros antes da deduplicação: %s",
        len(all_players),
    )

    df = transform_dataframe(all_players)

    validate_dataframe(df)

    save_parquet(df)

    logger.info("Arquivo salvo: %s", OUTPUT_FILE)
    logger.info("Total de jogadores: %s", len(df))
    logger.info("IDs únicos: %s", df["player_id"].nunique())

    logger.info(
        "Jogadores com data de nascimento: %s",
        df["birth_date"].notna().sum(),
    )

    logger.info(
        "Jogadores com altura: %s",
        df["height"].notna().sum(),
    )

    logger.info(
        "Jogadores com país: %s",
        df["country_name"].notna().sum(),
    )

    logger.info("Schema:")
    for column, dtype in df.dtypes.items():
        logger.info("%s: %s", column, dtype)


if __name__ == "__main__":
    main()