import json
import logging
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURAÇÕES
# ============================================================

RAW_PATH = Path("data/raw/lineups")
PROCESSED_PATH = Path("data/processed")

MATCHES_PATH = PROCESSED_PATH / "matches.parquet"
OUTPUT_PATH = PROCESSED_PATH / "lineups.parquet"

SIDES = ["home", "away"]
PLAYER_GROUPS = ["players"]

OUTPUT_COLUMNS = [
    "match_id",
    "team_id",
    "player_id",
    "player_name",
    "starter",
    "substitute",
    "position",
    "shirt_number",
    "captain",
    "formation",
    "side",
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
# CONVERSÕES
# ============================================================

def to_int(value):
    """
    Converte um valor para inteiro.

    Retorna None quando o valor é nulo ou inválido.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def to_bool(value, default=False):
    """
    Converte valores para booleano.

    Trata valores booleanos, numéricos e strings.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {"true", "1", "yes", "sim"}:
            return True

        if normalized in {"false", "0", "no", "não", "nao"}:
            return False

    return default


# ============================================================
# RELACIONAMENTO ENTRE PARTIDAS E EQUIPES
# ============================================================

def load_match_teams():
    """
    Carrega os IDs das equipes participantes de cada partida.

    A associação dos jogadores às equipes é determinada pelo
    lado da escalação:

        home -> home_team_id
        away -> away_team_id

    O teamId individual presente no JSON da escalação não é
    utilizado como referência da equipe da partida.
    """

    if not MATCHES_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de partidas não encontrado: {MATCHES_PATH}"
        )

    required_columns = [
        "match_id",
        "home_team_id",
        "away_team_id",
    ]

    matches = pd.read_parquet(
        MATCHES_PATH,
        columns=required_columns,
    )

    if matches.empty:
        raise ValueError(
            "O arquivo matches.parquet não contém partidas."
        )

    if matches["match_id"].duplicated().any():
        raise ValueError(
            "Existem match_id duplicados em matches.parquet."
        )

    if matches[required_columns].isna().any().any():
        raise ValueError(
            "Existem IDs ausentes em matches.parquet "
            "nas colunas match_id, home_team_id ou away_team_id."
        )

    for column in required_columns:
        matches[column] = matches[column].astype("int64")

    match_teams = (
        matches
        .set_index("match_id")[
            ["home_team_id", "away_team_id"]
        ]
        .to_dict("index")
    )

    return match_teams


# ============================================================
# LEITURA DOS JSONs
# ============================================================

def load_lineup_file(file):
    """
    Carrega e valida a estrutura básica de um JSON de escalação.

    Retorna um dicionário quando válido.
    Retorna None quando o arquivo não pode ser utilizado.
    """

    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

    except json.JSONDecodeError as error:
        logger.warning(
            f"JSON inválido: {file.name} | {error}"
        )
        return None

    except OSError as error:
        logger.warning(
            f"Erro ao ler {file.name}: {error}"
        )
        return None

    if not isinstance(data, dict):
        logger.warning(
            f"Estrutura inválida em {file.name}: "
            "a raiz do JSON não é um objeto."
        )
        return None

    if not any(
        isinstance(data.get(side), dict)
        for side in SIDES
    ):
        logger.warning(
            f"Estrutura inválida em {file.name}: "
            "nenhum lado home/away válido encontrado."
        )
        return None

    return data


# ============================================================
# EXTRAÇÃO DOS JOGADORES
# ============================================================

def extract_players(match_id, data, match_teams):
    """
    Extrai os jogadores de uma partida.

    A equipe é determinada pelo lado da escalação e pelo
    relacionamento com matches.parquet.

    O campo item["teamId"] do JSON não é utilizado.
    """

    records = []

    if match_id not in match_teams:
        logger.warning(
            f"Partida {match_id} não encontrada em matches.parquet."
        )
        return records

    for side in SIDES:

        side_data = data.get(side, {})

        if not isinstance(side_data, dict):
            continue

        # Associação correta da equipe à partida.
        team_id = match_teams[match_id][f"{side}_team_id"]

        formation = side_data.get("formation")

        for group in PLAYER_GROUPS:

            players = side_data.get(group, [])

            if not isinstance(players, list):
                logger.warning(
                    f"Lista inválida em {match_id} | "
                    f"{side} | {group}"
                )
                continue

            for item in players:

                if not isinstance(item, dict):
                    continue

                player = item.get("player", {})

                if not isinstance(player, dict) or not player:
                    continue

                player_id = to_int(player.get("id"))

                if player_id is None:
                    continue

                # A classificação é feita pelo campo substitute
                # do próprio registro do jogador.
                substitute = to_bool(
                    item.get("substitute", False)
                )

                starter = not substitute

                # O Sofascore pode fornecer ambos os campos.
                # shirtNumber é priorizado.
                shirt_number = to_int(
                    item.get("shirtNumber")
                )

                if shirt_number is None:
                    shirt_number = to_int(
                        item.get("jerseyNumber")
                    )

                records.append({
                    "match_id": match_id,
                    "team_id": team_id,
                    "player_id": player_id,
                    "player_name": player.get("name"),
                    "starter": starter,
                    "substitute": substitute,
                    "position": item.get("position"),
                    "shirt_number": shirt_number,
                    "captain": to_bool(
                        item.get("captain", False)
                    ),
                    "formation": formation,
                    "side": side,
                })

    return records


# ============================================================
# PROCESSAMENTO PRINCIPAL
# ============================================================

def main():

    logger.info("Iniciando transformação das escalações.")

    # --------------------------------------------------------
    # Verificação dos diretórios e arquivos
    # --------------------------------------------------------

    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"Diretório de escalações não encontrado: {RAW_PATH}"
        )

    PROCESSED_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_files = sorted(RAW_PATH.glob("*.json"))

    if not json_files:
        raise SystemExit(
            f"Nenhum arquivo encontrado em: {RAW_PATH}\n"
            "Execute primeiro: python scripts/extract/collect_lineups.py"
        )

    logger.info(
        f"Arquivos JSON encontrados: {len(json_files)}"
    )

    # --------------------------------------------------------
    # Carregamento do relacionamento das equipes
    # --------------------------------------------------------

    match_teams = load_match_teams()

    logger.info(
        f"Partidas disponíveis para associação: {len(match_teams)}"
    )

    # --------------------------------------------------------
    # Extração dos registros
    # --------------------------------------------------------

    lineups = []

    processed_files = 0
    invalid_files = 0
    empty_files = 0

    for file in json_files:

        match_id = to_int(file.stem)

        if match_id is None:
            logger.warning(
                f"Nome de arquivo com match_id inválido: {file.name}"
            )
            invalid_files += 1
            continue

        data = load_lineup_file(file)

        if data is None:
            invalid_files += 1
            continue

        records = extract_players(
            match_id,
            data,
            match_teams,
        )

        if not records:
            empty_files += 1
            continue

        lineups.extend(records)
        processed_files += 1

    logger.info(
        f"Arquivos processados: {processed_files}"
    )

    logger.info(
        f"Arquivos inválidos: {invalid_files}"
    )

    logger.info(
        f"Arquivos sem jogadores extraídos: {empty_files}"
    )

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(
        lineups,
        columns=OUTPUT_COLUMNS,
    )

    logger.info(
        f"Total de registros antes da deduplicação: {len(df)}"
    )

    if df.empty:
        raise SystemExit(
            "Nenhum jogador foi encontrado. "
            "O arquivo Parquet existente não será alterado."
        )

    # --------------------------------------------------------
    # Limpeza e deduplicação
    # --------------------------------------------------------

    df = df.dropna(
        subset=[
            "match_id",
            "team_id",
            "player_id",
        ]
    )

    df = df.drop_duplicates(
        subset=[
            "match_id",
            "team_id",
            "player_id",
        ]
    )

    logger.info(
        f"Total de registros após deduplicação: {len(df)}"
    )

    # --------------------------------------------------------
    # Tipagem
    # --------------------------------------------------------

    df["match_id"] = df["match_id"].astype("int64")
    df["team_id"] = df["team_id"].astype("int64")
    df["player_id"] = df["player_id"].astype("int64")

    df["starter"] = df["starter"].astype("bool")
    df["substitute"] = df["substitute"].astype("bool")
    df["captain"] = df["captain"].astype("bool")

    df["shirt_number"] = df["shirt_number"].astype("Int64")

    df["position"] = df["position"].astype("category")
    df["side"] = df["side"].astype("category")

    # --------------------------------------------------------
    # Ordenação
    # --------------------------------------------------------

    df = df.sort_values(
        ["match_id", "team_id", "starter"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Validações antes da gravação
    # --------------------------------------------------------

    if df[OUTPUT_COLUMNS].isna().any().any():
        # player_name, position, shirt_number e formation
        # podem ser ausentes na fonte. Os IDs, porém, não.
        required_id_columns = [
            "match_id",
            "team_id",
            "player_id",
        ]

        if df[required_id_columns].isna().any().any():
            raise ValueError(
                "Existem IDs nulos após a transformação."
            )

    inconsistent_classification = (
        df["starter"] == df["substitute"]
    )

    if inconsistent_classification.any():
        raise ValueError(
            "Foram encontrados jogadores com classificação "
            "inconsistente entre starter e substitute."
        )

    duplicated_players = df.duplicated(
        subset=[
            "match_id",
            "team_id",
            "player_id",
        ]
    )

    if duplicated_players.any():
        raise ValueError(
            "Foram encontrados registros duplicados."
        )

    # --------------------------------------------------------
    # Gravação atômica do Parquet
    # --------------------------------------------------------

    temp_path = PROCESSED_PATH / "lineups.tmp.parquet"

    try:

        df.to_parquet(
            temp_path,
            engine="pyarrow",
            compression="snappy",
            index=False,
        )

        # Confere o arquivo temporário antes de substituir
        # o Parquet definitivo.
        validation_df = pd.read_parquet(temp_path)

        if len(validation_df) != len(df):
            raise ValueError(
                "A quantidade de registros do Parquet "
                "não corresponde ao DataFrame original."
            )

        if list(validation_df.columns) != OUTPUT_COLUMNS:
            raise ValueError(
                "As colunas do Parquet gerado não correspondem "
                "ao schema esperado."
            )

        # Substituição atômica do arquivo definitivo.
        temp_path.replace(OUTPUT_PATH)

    except Exception:

        if temp_path.exists():
            temp_path.unlink()

        raise

    # --------------------------------------------------------
    # Resumo final
    # --------------------------------------------------------

    logger.info("=" * 60)
    logger.info("TRANSFORMAÇÃO CONCLUÍDA")
    logger.info("=" * 60)

    logger.info(
        f"Arquivo salvo em: {OUTPUT_PATH}"
    )

    logger.info(
        f"Total de registros: {len(df):,}"
    )

    logger.info(
        f"Partidas representadas: {df['match_id'].nunique():,}"
    )

    logger.info(
        f"Equipes representadas: {df['team_id'].nunique():,}"
    )

    logger.info(
        f"Jogadores únicos: {df['player_id'].nunique():,}"
    )

    logger.info(
        f"Titulares: {df['starter'].sum():,}"
    )

    logger.info(
        f"Reservas: {df['substitute'].sum():,}"
    )

    logger.info(
        f"\nSchema:\n{df.dtypes}"
    )

    logger.info(
        f"\nAmostra:\n{df.head(10).to_string(index=False)}"
    )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()
