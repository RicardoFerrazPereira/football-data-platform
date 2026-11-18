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

PROCESSED_PATH = Path("data/processed")

MATCHES_PATH = PROCESSED_PATH / "matches.parquet"

OUTPUT_FILE = PROCESSED_PATH / "teams.parquet"

TEMP_FILE = PROCESSED_PATH / "teams.tmp.parquet"

REQUIRED_COLUMNS = {
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
}


# =====================================
# LOAD MATCHES
# =====================================

def load_matches() -> pd.DataFrame:

    if not MATCHES_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {MATCHES_PATH}\n"
            "Execute primeiro: python transform_matches.py"
        )

    matches = pd.read_parquet(MATCHES_PATH)

    if matches.empty:
        raise ValueError(
            "O arquivo matches.parquet está vazio."
        )

    missing_columns = REQUIRED_COLUMNS - set(matches.columns)

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            f"{sorted(missing_columns)}"
        )

    logger.info(
        f"Partidas carregadas: {len(matches)}"
    )

    return matches


# =====================================
# EXTRACT HOME AND AWAY TEAMS
# =====================================

def extract_teams(matches: pd.DataFrame) -> pd.DataFrame:

    home_teams = matches[
        ["home_team_id", "home_team_name"]
    ].copy()

    home_teams.columns = [
        "team_id",
        "team_name",
    ]

    away_teams = matches[
        ["away_team_id", "away_team_name"]
    ].copy()

    away_teams.columns = [
        "team_id",
        "team_name",
    ]

    teams = pd.concat(
        [home_teams, away_teams],
        ignore_index=True,
    )

    logger.info(
        f"Registros de times antes da limpeza: {len(teams)}"
    )

    return teams


# =====================================
# CLEAN TEAM DATA
# =====================================

def clean_teams(teams: pd.DataFrame) -> pd.DataFrame:

    teams = teams.copy()

    # ---------------------------------
    # TEAM ID
    # ---------------------------------

    original_ids = teams["team_id"]

    numeric_ids = pd.to_numeric(
        original_ids,
        errors="coerce",
    )

    invalid_ids = (
        original_ids.notna()
        & numeric_ids.isna()
    )

    if invalid_ids.any():
        examples = original_ids[invalid_ids].head(10).tolist()

        raise ValueError(
            "Foram encontrados IDs de times não numéricos. "
            f"Exemplos: {examples}"
        )

    # Verifica se existem IDs fracionários.
    non_integer_ids = (
        numeric_ids.notna()
        & (numeric_ids % 1 != 0)
    )

    if non_integer_ids.any():
        examples = numeric_ids[non_integer_ids].head(10).tolist()

        raise ValueError(
            "Foram encontrados IDs de times não inteiros. "
            f"Exemplos: {examples}"
        )

    # ---------------------------------
    # TEAM NAME
    # ---------------------------------

    teams["team_name"] = (
        teams["team_name"]
        .astype("string")
        .str.strip()
    )

    # Trata nomes vazios como valores ausentes.
    teams["team_name"] = teams["team_name"].replace(
        "",
        pd.NA,
    )

    # ---------------------------------
    # REMOVE NULLS
    # ---------------------------------

    rows_before = len(teams)

    teams = teams.dropna(
        subset=["team_id", "team_name"]
    ).copy()

    removed_rows = rows_before - len(teams)

    if removed_rows:
        logger.warning(
            f"Registros removidos por ID ou nome ausente: "
            f"{removed_rows}"
        )

    if teams.empty:
        raise ValueError(
            "Nenhum registro válido de time foi encontrado."
        )

    # ---------------------------------
    # CONVERT TYPES
    # ---------------------------------

    teams["team_id"] = teams["team_id"].astype("int64")

    teams["team_name"] = teams["team_name"].astype("string")

    return teams


# =====================================
# RESOLVE TEAM NAME CONFLICTS
# =====================================

def consolidate_teams(teams: pd.DataFrame) -> pd.DataFrame:

    # Identifica IDs associados a mais de um nome.
    name_counts = (
        teams.groupby("team_id")["team_name"]
        .nunique()
    )

    conflicting_ids = name_counts[
        name_counts > 1
    ].index

    if len(conflicting_ids):
        logger.warning(
            f"IDs com nomes diferentes no histórico: "
            f"{len(conflicting_ids)}"
        )

    consolidated_records = []

    for team_id, group in teams.groupby(
        "team_id",
        sort=False,
    ):

        counts = group["team_name"].value_counts()

        # Maior frequência primeiro; desempate alfabético.
        ordered_names = sorted(
            counts.items(),
            key=lambda item: (-item[1], str(item[0]).casefold()),
        )

        selected_name = ordered_names[0][0]

        if len(ordered_names) > 1:
            alternatives = ", ".join(
                f"{name} ({count})"
                for name, count in ordered_names
            )

            logger.warning(
                f"Team ID {team_id}: nomes divergentes: "
                f"{alternatives}. "
                f"Nome selecionado: {selected_name}"
            )

        consolidated_records.append(
            {
                "team_id": team_id,
                "team_name": selected_name,
            }
        )

    teams = pd.DataFrame(
        consolidated_records,
        columns=["team_id", "team_name"],
    )

    teams["team_id"] = teams["team_id"].astype("int64")

    teams["team_name"] = teams["team_name"].astype("string")

    teams = (
        teams.sort_values(
            "team_name",
            key=lambda column: column.str.casefold(),
        )
        .reset_index(drop=True)
    )

    return teams


# =====================================
# VALIDATE TEAMS
# =====================================

def validate_teams(teams: pd.DataFrame) -> None:

    if teams.empty:
        raise ValueError(
            "A tabela de times está vazia."
        )

    if teams["team_id"].isna().any():
        raise ValueError(
            "Existem IDs de times nulos."
        )

    if teams["team_name"].isna().any():
        raise ValueError(
            "Existem nomes de times nulos."
        )

    if teams["team_id"].duplicated().any():
        raise ValueError(
            "Existem IDs de times duplicados."
        )

    if teams["team_id"].dtype != "int64":
        raise TypeError(
            "team_id deveria possuir tipo int64."
        )

    if str(teams["team_name"].dtype) != "string":
        raise TypeError(
            "team_name deveria possuir tipo string."
        )

    logger.info(
        "Validação dos dados concluída."
    )


# =====================================
# SAVE PARQUET ATOMICALLY
# =====================================

def save_parquet(teams: pd.DataFrame) -> None:

    PROCESSED_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        teams.to_parquet(
            TEMP_FILE,
            engine="pyarrow",
            compression="snappy",
            index=False,
        )

        # Confere o arquivo antes de substituir o definitivo.
        check = pd.read_parquet(TEMP_FILE)

        if len(check) != len(teams):
            raise ValueError(
                "A quantidade de registros do Parquet "
                "não corresponde à tabela original."
            )

        if list(check.columns) != list(teams.columns):
            raise ValueError(
                "As colunas do Parquet não correspondem "
                "à tabela original."
            )

        if check["team_id"].duplicated().any():
            raise ValueError(
                "O Parquet contém IDs duplicados."
            )

        os.replace(
            TEMP_FILE,
            OUTPUT_FILE,
        )

        logger.info(
            f"Arquivo salvo: {OUTPUT_FILE}"
        )

    finally:
        if TEMP_FILE.exists():
            TEMP_FILE.unlink()


# =====================================
# FINAL REPORT
# =====================================

def log_final_report(teams: pd.DataFrame) -> None:

    logger.info("")
    logger.info("=" * 60)
    logger.info("TRANSFORMAÇÃO DE TIMES FINALIZADA")
    logger.info("=" * 60)

    logger.info(
        f"Total de times: {len(teams)}"
    )

    logger.info(
        f"IDs únicos: {teams['team_id'].nunique()}"
    )

    logger.info(
        f"IDs nulos: {teams['team_id'].isna().sum()}"
    )

    logger.info(
        f"Nomes nulos: {teams['team_name'].isna().sum()}"
    )

    logger.info(
        f"IDs duplicados: {teams['team_id'].duplicated().sum()}"
    )

    logger.info(
        f"\nSchema:\n{teams.dtypes}"
    )

    logger.info(
        f"\nAmostra:\n{teams.head(10).to_string(index=False)}"
    )

    logger.info(
        f"\nArquivo: {OUTPUT_FILE}"
    )


# =====================================
# MAIN
# =====================================

def main():

    matches = load_matches()

    teams = extract_teams(matches)

    teams = clean_teams(teams)

    teams = consolidate_teams(teams)

    validate_teams(teams)

    save_parquet(teams)

    log_final_report(teams)


if __name__ == "__main__":
    main()
