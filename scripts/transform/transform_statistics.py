
import json
import logging
import math
import os
import tempfile
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURAÇÕES
# ============================================================

RAW_PATH = Path("data/raw/statistics")
PROCESSED_PATH = Path("data/processed")
OUTPUT_FILE = PROCESSED_PATH / "statistics.parquet"

SIDES = ("home", "away")

OUTPUT_COLUMNS = [
    "match_id",
    "period",
    "group_name",
    "statistic_key",
    "statistic_name",
    "statistics_type",
    "value_type",
    "team_side",
    "value",
    "value_numeric",
]

# Chave lógica que identifica cada registro.
KEY_COLUMNS = [
    "match_id",
    "period",
    "group_name",
    "statistic_key",
    "team_side",
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
# VALIDAÇÃO DOS DADOS
# ============================================================

def validate_text_field(value, field_name, file_path):
    """Valida campos textuais obrigatórios."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Campo '{field_name}' ausente ou inválido "
            f"no arquivo {file_path}"
        )

    return value


def validate_numeric_field(value, field_name, file_path):
    """Valida valores numéricos de origem."""

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(
            f"Campo '{field_name}' não numérico ou inválido "
            f"no arquivo {file_path}: {value!r}"
        )

    return float(value)


def load_statistics_file(file_path):
    """Carrega e valida um JSON de estatísticas."""

    try:
        match_id = int(file_path.stem)
    except ValueError as exc:
        raise ValueError(
            f"Nome de arquivo não representa um match_id válido: "
            f"{file_path.name}"
        ) from exc

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(
            f"Não foi possível ler o JSON {file_path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"A raiz do JSON deve ser um objeto: {file_path}"
        )

    statistics = data.get("statistics")

    if not isinstance(statistics, list) or not statistics:
        raise ValueError(
            f"Campo 'statistics' ausente, vazio ou inválido: {file_path}"
        )

    records = []

    for period in statistics:

        if not isinstance(period, dict):
            raise ValueError(
                f"Período inválido em {file_path}"
            )

        period_name = validate_text_field(
            period.get("period"),
            "period",
            file_path,
        )

        groups = period.get("groups")

        if not isinstance(groups, list):
            raise ValueError(
                f"Campo 'groups' inválido no período "
                f"{period_name}: {file_path}"
            )

        for group in groups:

            if not isinstance(group, dict):
                raise ValueError(
                    f"Grupo inválido no período {period_name}: {file_path}"
                )

            group_name = validate_text_field(
                group.get("groupName"),
                "groupName",
                file_path,
            )

            items = group.get("statisticsItems")

            if not isinstance(items, list):
                raise ValueError(
                    f"Campo 'statisticsItems' inválido "
                    f"no grupo {group_name}: {file_path}"
                )

            for item in items:

                if not isinstance(item, dict):
                    raise ValueError(
                        f"Item de estatística inválido "
                        f"no grupo {group_name}: {file_path}"
                    )

                statistic_key = validate_text_field(
                    item.get("key"),
                    "key",
                    file_path,
                )

                statistic_name = validate_text_field(
                    item.get("name"),
                    "name",
                    file_path,
                )

                statistics_type = validate_text_field(
                    item.get("statisticsType"),
                    "statisticsType",
                    file_path,
                )

                value_type = validate_text_field(
                    item.get("valueType"),
                    "valueType",
                    file_path,
                )

                for side in SIDES:

                    value = validate_text_field(
                        item.get(side),
                        side,
                        file_path,
                    )

                    numeric_value = validate_numeric_field(
                        item.get(f"{side}Value"),
                        f"{side}Value",
                        file_path,
                    )

                    records.append({
                        "match_id": match_id,
                        "period": period_name,
                        "group_name": group_name,
                        "statistic_key": statistic_key,
                        "statistic_name": statistic_name,
                        "statistics_type": statistics_type,
                        "value_type": value_type,
                        "team_side": side,
                        "value": value,
                        "value_numeric": numeric_value,
                    })

    if not records:
        raise ValueError(
            f"Nenhum registro de estatística encontrado: {file_path}"
        )

    return records


# ============================================================
# TRANSFORMAÇÃO
# ============================================================

def build_dataframe(json_files):
    """Transforma os JSONs em um DataFrame validado."""

    statistics_data = []

    for file_path in json_files:
        records = load_statistics_file(file_path)
        statistics_data.extend(records)

        logger.info(
            f"Arquivo processado: {file_path.name} "
            f"({len(records)} registros)"
        )

    if not statistics_data:
        raise ValueError("Nenhum registro de estatística foi encontrado.")

    df = pd.DataFrame(
        statistics_data,
        columns=OUTPUT_COLUMNS,
    )

    # Tipagem explícita.
    df["match_id"] = df["match_id"].astype("int64")

    string_columns = [
        "period",
        "group_name",
        "statistic_key",
        "statistic_name",
        "statistics_type",
        "value_type",
        "team_side",
        "value",
    ]

    for column in string_columns:
        df[column] = df[column].astype("string")

    df["value_numeric"] = df["value_numeric"].astype("float64")

    # Verifica a chave lógica sem descartar registros.
    duplicated_mask = df.duplicated(
        subset=KEY_COLUMNS,
        keep=False,
    )

    if duplicated_mask.any():
        examples = (
            df.loc[duplicated_mask, KEY_COLUMNS]
            .head(10)
            .to_string(index=False)
        )

        raise ValueError(
            "Foram encontradas combinações duplicadas na chave lógica.\n"
            f"Exemplos:\n{examples}"
        )

    # Ordenação determinística.
    df = df.sort_values(
        KEY_COLUMNS,
        kind="mergesort",
    ).reset_index(drop=True)

    return df


# ============================================================
# GRAVAÇÃO ATÔMICA
# ============================================================

def save_parquet_atomic(df, output_file):
    """Grava o Parquet temporariamente e substitui o destino ao concluir."""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_file.stem}_",
            suffix=".parquet",
            dir=output_file.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        df.to_parquet(
            temp_path,
            engine="pyarrow",
            compression="snappy",
            index=False,
        )

        # Confirma que o arquivo temporário pode ser lido.
        check_df = pd.read_parquet(
            temp_path,
            engine="pyarrow",
        )

        if len(check_df) != len(df):
            raise ValueError(
                "A quantidade de registros do Parquet temporário "
                "não corresponde ao DataFrame original."
            )

        if list(check_df.columns) != OUTPUT_COLUMNS:
            raise ValueError(
                "O schema do Parquet temporário não corresponde "
                "ao schema esperado."
            )

        # Substituição atômica no mesmo diretório.
        os.replace(temp_path, output_file)
        temp_path = None

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():

    logger.info("Iniciando transformação das estatísticas.")

    json_files = sorted(RAW_PATH.glob("*.json"))

    if not json_files:
        raise SystemExit(
            f"Nenhum arquivo encontrado em: {RAW_PATH}\n"
            "Execute primeiro: python collect_statistics.py"
        )

    logger.info(f"Arquivos encontrados: {len(json_files)}")

    # Carrega os IDs das partidas existentes em matches.parquet.
    matches_file = PROCESSED_PATH / "matches.parquet"

    if not matches_file.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {matches_file}"
        )

    matches_df = pd.read_parquet(
        matches_file,
        columns=["match_id"],
    )

    match_ids = set(matches_df["match_id"].astype("int64"))

    # Identifica arquivos sem correspondência em matches.parquet.
    arquivos_ignorados = [
        file
        for file in json_files
        if int(file.stem) not in match_ids
    ]

    # Mantém somente os arquivos de partidas válidas.
    json_files = [
        file
        for file in json_files
        if int(file.stem) in match_ids
    ]

    if arquivos_ignorados:
        logger.warning(
            f"Arquivos ignorados por não constarem em matches.parquet: "
            f"{len(arquivos_ignorados)}"
        )

        for file in arquivos_ignorados:
            logger.warning(f"Partida ignorada: {file.stem}")

    logger.info(
        f"Arquivos que serão processados: {len(json_files)}"
    )

    # Toda a leitura e validação ocorre antes de substituir o Parquet.
    df = build_dataframe(json_files)

    logger.info(f"Total de registros: {len(df)}")
    logger.info(
        f"Partidas distintas: {df['match_id'].nunique()}"
    )

    logger.info(
        "Combinações únicas da chave lógica: "
        f"{len(df.drop_duplicates(subset=KEY_COLUMNS))}"
    )

    save_parquet_atomic(df, OUTPUT_FILE)

    logger.info(f"Arquivo salvo em: {OUTPUT_FILE}")
    logger.info(f"Total de registros: {len(df)}")
    logger.info(f"\nSchema:\n{df.dtypes}")
    logger.info(f"\nAmostra:\n{df.head(10).to_string(index=False)}")

    logger.info("Transformação concluída com sucesso.")


if __name__ == "__main__":
    main()
