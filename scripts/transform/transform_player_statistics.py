
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

RAW_PATH = Path("data/raw/lineups")
PROCESSED_PATH = Path("data/processed")

MATCHES_FILE = PROCESSED_PATH / "matches.parquet"
OUTPUT_FILE = PROCESSED_PATH / "player_statistics.parquet"

SIDES = ["home", "away"]
PLAYER_GROUPS = ["players", "substitutes"]

# Campos auxiliares, não são métricas de desempenho.
IGNORED_STATISTICS = {"statisticsType"}

# Colunas utilizadas para identificar uma estatística individual.
LOGICAL_KEY = [
    "match_id",
    "side",
    "player_id",
    "statistic_name",
]

EXPECTED_COLUMNS = [
    "match_id",
    "team_id",
    "player_id",
    "player_name",
    "side",
    "position",
    "substitute",
    "statistic_name",
    "value",
    "value_numeric",
]


# =====================================
# LOAD MATCHES
# =====================================

def load_matches():
    """
    Carrega as partidas e prepara a associação entre
    match_id, home_team_id e away_team_id.
    """

    if not MATCHES_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo de partidas não encontrado: {MATCHES_FILE}"
        )

    matches = pd.read_parquet(
        MATCHES_FILE,
        columns=[
            "match_id",
            "home_team_id",
            "away_team_id",
        ],
    )

    if matches.empty:
        raise ValueError("matches.parquet está vazio.")

    if matches.isnull().any().any():
        raise ValueError(
            "matches.parquet contém valores nulos "
            "nas colunas de identificação."
        )

    matches["match_id"] = pd.to_numeric(
        matches["match_id"],
        errors="raise",
    ).astype("int64")

    matches["home_team_id"] = pd.to_numeric(
        matches["home_team_id"],
        errors="raise",
    ).astype("int64")

    matches["away_team_id"] = pd.to_numeric(
        matches["away_team_id"],
        errors="raise",
    ).astype("int64")

    if matches["match_id"].duplicated().any():
        raise ValueError(
            "matches.parquet contém match_id duplicados."
        )

    home_teams = matches.set_index("match_id")["home_team_id"]
    away_teams = matches.set_index("match_id")["away_team_id"]

    logger.info(
        f"Partidas carregadas para associação: {len(matches)}"
    )

    return home_teams.to_dict(), away_teams.to_dict()


# =====================================
# NORMALIZE SUBSTITUTE
# =====================================

def normalize_substitute(value, group):
    """
    Normaliza o indicador de reserva.

    Quando o campo não está presente no JSON,
    utiliza o grupo de origem como referência.
    """

    if value is None:
        return group == "substitutes"

    if isinstance(value, bool):
        return value

    if isinstance(value, int) and value in (0, 1):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized == "true":
            return True

        if normalized == "false":
            return False

    raise ValueError(
        f"Valor inválido para substitute: {value!r}"
    )


# =====================================
# EXTRACT PLAYER STATISTICS
# =====================================


def extract_statistics(home_teams, away_teams, json_files):

    statistics_data = []

    files_processed = 0
    files_without_players = 0
    players_without_statistics = 0
    nested_values_ignored = 0
    invalid_players = 0

    for file in json_files:

        try:
            match_id = int(file.stem)

            with file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError(
                    "A raiz do JSON não é um objeto."
                )

            # Verifica se existem jogadores em qualquer lado.
            has_players = False

            for side in SIDES:

                side_data = data.get(side) or {}

                if not isinstance(side_data, dict):
                    raise ValueError(
                        f"Estrutura inválida para o lado {side}."
                    )

                for group in PLAYER_GROUPS:

                    players = side_data.get(group) or []

                    if not isinstance(players, list):
                        raise ValueError(
                            f"Grupo {group} não é uma lista."
                        )

                    if players:
                        has_players = True

            # JSON sem jogadores não precisa de associação com a partida.
            if not has_players:
                files_without_players += 1
                logger.info(
                    f"Arquivo sem jogadores ignorado: {file.name}"
                )
                continue

            # Se existem jogadores, a partida precisa estar cadastrada.
            if match_id not in home_teams or match_id not in away_teams:
                raise ValueError(
                    f"Partida {match_id} não encontrada "
                    "ou sem associação completa em matches.parquet."
                )

            for side in SIDES:

                side_data = data.get(side) or {}

                if side == "home":
                    team_id = home_teams[match_id]
                else:
                    team_id = away_teams[match_id]

                for group in PLAYER_GROUPS:

                    players = side_data.get(group) or []

                    for item in players:

                        if not isinstance(item, dict):
                            raise ValueError(
                                f"Jogador com estrutura inválida em {group}."
                            )

                        player = item.get("player") or {}

                        if not isinstance(player, dict):
                            raise ValueError(
                                "Campo player não é um objeto."
                            )

                        player_id = player.get("id")

                        if player_id is None:
                            invalid_players += 1
                            raise ValueError(
                                f"Jogador sem ID na partida {match_id}."
                            )

                        player_id = int(player_id)

                        statistics = item.get("statistics") or {}

                        if not isinstance(statistics, dict):
                            raise ValueError(
                                f"Estatísticas inválidas para "
                                f"o jogador {player_id}."
                            )

                        if not statistics:
                            players_without_statistics += 1
                            continue

                        substitute = normalize_substitute(
                            item.get("substitute"),
                            group,
                        )

                        for stat_name, stat_value in statistics.items():

                            # Ignora campos auxiliares.
                            if stat_name in IGNORED_STATISTICS:
                                continue

                            # Ignora valores aninhados, como ratingVersions.
                            if isinstance(stat_value, (dict, list)):
                                nested_values_ignored += 1
                                continue

                            statistics_data.append({
                                "match_id": match_id,
                                "team_id": team_id,
                                "player_id": player_id,
                                "player_name": player.get("name"),
                                "side": side,
                                "position": item.get("position"),
                                "substitute": substitute,
                                "statistic_name": stat_name,
                                "value": stat_value,
                            })

            files_processed += 1

        except Exception as e:
            raise RuntimeError(
                f"Erro ao processar {file.name}: {e}"
            ) from e

    logger.info(f"Arquivos processados: {files_processed}")
    logger.info(f"Arquivos sem jogadores: {files_without_players}")
    logger.info(
        f"Jogadores sem estatísticas: {players_without_statistics}"
    )
    logger.info(f"Jogadores com IDs inválidos: {invalid_players}")
    logger.info(f"Valores aninhados ignorados: {nested_values_ignored}")

    return statistics_data



# =====================================
# BUILD DATAFRAME
# =====================================

def build_dataframe(statistics_data):

    df = pd.DataFrame(statistics_data)

    if df.empty:
        raise ValueError(
            "Nenhuma estatística encontrada nos arquivos de entrada."
        )

    logger.info(f"Total de registros extraídos: {len(df)}")

    # =================================
    # VALIDATE IDS
    # =================================

    id_columns = [
        "match_id",
        "team_id",
        "player_id",
    ]

    for column in id_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="raise",
        )

        if df[column].isnull().any():
            raise ValueError(
                f"A coluna {column} contém valores nulos."
            )

        df[column] = df[column].astype("int64")

    # =================================
    # VALIDATE LOGICAL KEY
    # =================================

    duplicated = df.duplicated(
        subset=LOGICAL_KEY,
        keep=False,
    )

    if duplicated.any():

        examples = df.loc[
            duplicated,
            LOGICAL_KEY,
        ].head(10)

        raise ValueError(
            "Foram encontradas combinações duplicadas "
            "na chave lógica:\n"
            f"{examples.to_string(index=False)}"
        )

    logger.info(
        "Validação da chave lógica aprovada. "
        "Nenhuma duplicidade encontrada."
    )

    # =================================
    # VALUE NUMERIC
    # =================================

    df["value_numeric"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    ).astype("float64")

    # Preserva o valor original em formato textual.
    df["value"] = df["value"].astype("string")

    # =================================
    # STRING COLUMNS
    # =================================

    string_columns = [
        "player_name",
        "side",
        "position",
        "statistic_name",
    ]

    for column in string_columns:
        df[column] = df[column].astype("string")

    # =================================
    # SUBSTITUTE
    # =================================

    df["substitute"] = df["substitute"].astype(bool)

    # =================================
    # SORT
    # =================================

    df = df.sort_values(
        [
            "match_id",
            "team_id",
            "player_id",
            "statistic_name",
        ]
    ).reset_index(drop=True)

    # =================================
    # COLUMN ORDER
    # =================================

    df = df[EXPECTED_COLUMNS]

    return df


# =====================================
# SAVE ATOMICALLY
# =====================================

def save_parquet_atomic(df):

    PROCESSED_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = PROCESSED_PATH / (
        f".{OUTPUT_FILE.stem}.tmp.parquet"
    )

    try:

        df.to_parquet(
            temp_file,
            engine="pyarrow",
            compression="snappy",
            index=False,
        )

        # Confere o arquivo temporário antes de substituir o destino.
        check_df = pd.read_parquet(temp_file)

        if len(check_df) != len(df):
            raise ValueError(
                "A quantidade de registros do Parquet "
                "não corresponde à quantidade original."
            )

        if list(check_df.columns) != EXPECTED_COLUMNS:
            raise ValueError(
                "O schema do Parquet gerado está incorreto."
            )

        if check_df["match_id"].isnull().any():
            raise ValueError("match_id contém valores nulos no Parquet.")

        if check_df["team_id"].isnull().any():
            raise ValueError("team_id contém valores nulos no Parquet.")

        if check_df["player_id"].isnull().any():
            raise ValueError("player_id contém valores nulos no Parquet.")

        if check_df.duplicated(subset=LOGICAL_KEY).any():
            raise ValueError(
                "O Parquet gerado contém chaves lógicas duplicadas."
            )

        # Substituição atômica do arquivo de destino.
        os.replace(temp_file, OUTPUT_FILE)

    finally:

        if temp_file.exists():
            temp_file.unlink()

    logger.info(f"Arquivo salvo em: {OUTPUT_FILE}")


# =====================================
# MAIN
# =====================================

def main():

    logger.info("=" * 50)
    logger.info("INICIANDO TRANSFORMAÇÃO DE ESTATÍSTICAS")
    logger.info("=" * 50)

    if not RAW_PATH.exists():
        raise SystemExit(
            f"Diretório não encontrado: {RAW_PATH}"
        )

    json_files = sorted(RAW_PATH.glob("*.json"))

    if not json_files:
        raise SystemExit(
            f"Nenhum arquivo encontrado em: {RAW_PATH}\n"
            "Execute primeiro: python collect_lineups.py"
        )

    logger.info(f"Arquivos encontrados: {len(json_files)}")

    home_teams, away_teams = load_matches()

    # Processa somente arquivos de partidas existentes em matches.parquet.
    match_ids = set(home_teams.keys())

    arquivos_ignorados = [
        file
        for file in json_files
        if int(file.stem) not in match_ids
    ]

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
            logger.warning(
                f"Partida ignorada: {file.stem}"
            )

    logger.info(
        f"Arquivos que serão processados: {len(json_files)}"
    )

    statistics_data = extract_statistics(
        home_teams,
        away_teams,
        json_files,
    )

    df = build_dataframe(statistics_data)

    save_parquet_atomic(df)

    # =================================
    # FINAL LOG
    # =================================

    logger.info("=" * 50)
    logger.info("TRANSFORMAÇÃO FINALIZADA COM SUCESSO")
    logger.info("=" * 50)

    logger.info(f"Total de registros: {len(df)}")
    logger.info(
        f"Partidas distintas: {df['match_id'].nunique()}"
    )
    logger.info(
        f"Jogadores distintos: {df['player_id'].nunique()}"
    )
    logger.info(
        f"Equipes distintas: {df['team_id'].nunique()}"
    )

    logger.info(
        f"\nValores nulos:\n{df.isnull().sum()}"
    )

    logger.info(
        f"\nMétricas disponíveis:\n"
        f"{sorted(df['statistic_name'].unique().tolist())}"
    )

    logger.info(f"\nSchema:\n{df.dtypes}")

    logger.info(
        f"\nAmostra:\n{df.head(10).to_string(index=False)}"
    )


if __name__ == "__main__":
    main()
