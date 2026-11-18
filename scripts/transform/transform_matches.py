
import json
import logging
import os
from pathlib import Path

import pandas as pd


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

MATCHES_PATH = Path("data/raw/matches/matches.json")

PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = PROCESSED_PATH / "matches.parquet"
TEMP_FILE = PROCESSED_PATH / "matches.tmp.parquet"

REQUIRED_COLUMNS = {
    "match_id",
    "match_date",
    "home_team_id",
    "away_team_id",
}


# =====================================
# LOAD JSON
# =====================================

def load_matches() -> list:

    if not MATCHES_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {MATCHES_PATH}\n"
            "Execute primeiro: python collect_matches.py"
        )

    logger.info(f"Lendo arquivo: {MATCHES_PATH}")

    with open(MATCHES_PATH, "r", encoding="utf-8") as file:
        matches = json.load(file)

    if not isinstance(matches, list):
        raise ValueError(
            "Estrutura inválida: o JSON deve conter uma lista de partidas."
        )

    if not matches:
        raise ValueError(
            "O arquivo JSON não contém partidas. "
            "A transformação foi interrompida."
        )

    invalid_records = [
        index
        for index, record in enumerate(matches)
        if not isinstance(record, dict)
    ]

    if invalid_records:
        raise ValueError(
            f"Foram encontrados {len(invalid_records)} registros "
            "que não são objetos JSON. "
            f"Exemplos de posições: {invalid_records[:10]}"
        )

    logger.info(f"Registros carregados: {len(matches)}")

    return matches


# =====================================
# CREATE DATAFRAME
# =====================================

def create_dataframe(matches: list) -> pd.DataFrame:

    df = pd.DataFrame(matches)

    logger.info(
        f"Total de linhas antes da deduplicação: {len(df)}"
    )

    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Colunas obrigatórias ausentes: "
            f"{sorted(missing_columns)}"
        )

    return df


# =====================================
# VALIDATE MATCH IDs
# =====================================

def validate_match_ids(df: pd.DataFrame) -> pd.DataFrame:

    missing_ids = df["match_id"].isna().sum()

    if missing_ids:
        raise ValueError(
            f"Foram encontradas {missing_ids} partidas sem match_id. "
            "A transformação foi interrompida."
        )

    # IDs de partidas devem ser numéricos e inteiros.
    numeric_ids = pd.to_numeric(
        df["match_id"],
        errors="coerce",
    )

    invalid_ids = numeric_ids.isna()

    if invalid_ids.any():
        raise ValueError(
            f"Foram encontrados {invalid_ids.sum()} match_id inválidos."
        )

    non_integer_ids = numeric_ids % 1 != 0

    if non_integer_ids.any():
        raise ValueError(
            "Foram encontrados match_id que não são números inteiros."
        )

    df["match_id"] = numeric_ids.astype("int64")

    return df


# =====================================
# REMOVE DUPLICATES
# =====================================

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:

    duplicates = df["match_id"].duplicated().sum()

    if duplicates:
        logger.warning(
            f"Partidas duplicadas encontradas: {duplicates}"
        )

    # Mantém o primeiro registro, preservando o comportamento anterior.
    df = df.drop_duplicates(
        subset=["match_id"],
        keep="first",
    ).copy()

    logger.info(
        f"Total de linhas após deduplicação: {len(df)}"
    )

    return df


# =====================================
# DATE CONVERSION
# =====================================

def convert_dates(df: pd.DataFrame) -> pd.DataFrame:

    df["match_date"] = pd.to_datetime(
        df["match_date"],
        errors="coerce",
        utc=True,
    )

    invalid_dates = df["match_date"].isna().sum()

    if invalid_dates:
        logger.warning(
            f"Partidas com datas inválidas ou ausentes: {invalid_dates}"
        )

    # Remove timezone para compatibilidade com o Parquet
    # e preserva a data/hora no padrão UTC.
    df["match_date"] = (
        df["match_date"]
        .dt.tz_localize(None)
    )

    return df


# =====================================
# SORT
# =====================================

def sort_matches(df: pd.DataFrame) -> pd.DataFrame:

    df = df.sort_values(
        by="match_date",
        ascending=True,
        na_position="last",
    ).reset_index(drop=True)

    return df


# =====================================
# SAVE PARQUET
# =====================================

def save_parquet(df: pd.DataFrame):

    try:

        # Grava primeiro em arquivo temporário.
        df.to_parquet(
            TEMP_FILE,
            engine="pyarrow",
            index=False,
        )

        # Valida o arquivo temporário antes de substituir o definitivo.
        validation_df = pd.read_parquet(TEMP_FILE)

        if len(validation_df) != len(df):
            raise ValueError(
                "A quantidade de registros do Parquet "
                "não corresponde ao DataFrame original."
            )

        if list(validation_df.columns) != list(df.columns):
            raise ValueError(
                "As colunas do Parquet não correspondem "
                "ao DataFrame original."
            )

        # Substitui o arquivo definitivo somente após validação.
        os.replace(TEMP_FILE, OUTPUT_FILE)

        logger.info(
            f"Arquivo salvo e validado: {OUTPUT_FILE}"
        )

    finally:

        if TEMP_FILE.exists():
            TEMP_FILE.unlink()


# =====================================
# FINAL REPORT
# =====================================

def log_final_report(df: pd.DataFrame):

    logger.info("")
    logger.info("=" * 50)
    logger.info("TRANSFORMAÇÃO DE PARTIDAS FINALIZADA")
    logger.info("=" * 50)

    logger.info(f"Total de partidas: {len(df)}")

    logger.info(
        f"IDs únicos: {df['match_id'].nunique()}"
    )

    logger.info(
        f"Partidas sem data: {df['match_date'].isna().sum()}"
    )

    valid_dates = df["match_date"].dropna()

    if not valid_dates.empty:

        logger.info(
            f"Período: {valid_dates.min().date()} "
            f"→ {valid_dates.max().date()}"
        )

    logger.info(f"Arquivo: {OUTPUT_FILE}")

    logger.info(
        f"\nSchema:\n{df.dtypes}"
    )


# =====================================
# MAIN
# =====================================

def main():

    logger.info("=" * 50)
    logger.info("TRANSFORMAÇÃO DAS PARTIDAS")
    logger.info("=" * 50)

    matches = load_matches()

    df = create_dataframe(matches)

    df = validate_match_ids(df)

    df = remove_duplicates(df)

    df = convert_dates(df)

    df = sort_matches(df)

    save_parquet(df)

    log_final_report(df)


if __name__ == "__main__":
    main()
