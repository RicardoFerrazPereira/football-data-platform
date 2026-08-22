import json
from pathlib import Path

import pandas as pd

# =====================================
# CONFIG
# =====================================

RAW_PATH = Path("data/raw/lineups")

PROCESSED_PATH = Path("data/processed")

PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

# =====================================
# FILES
# =====================================

json_files = list(RAW_PATH.glob("*.json"))

print(f"Arquivos encontrados: {len(json_files)}")

# =====================================
# STORAGE
# =====================================

lineups = []

# =====================================
# LOOP FILES
# =====================================

for file in json_files:

    match_id = int(file.stem)

    print(f"Lendo: {file.name}")

    with open(file, "r", encoding="utf-8") as f:

        data = json.load(f)

    # =====================================
    # SIDES
    # =====================================

    for side in ["home", "away"]:

        side_data = data.get(side, {})

        if not side_data:
            continue

        # =====================================
        # FORMATION
        # =====================================

        formation = side_data.get("formation")

        # =====================================
        # PLAYERS
        # =====================================

        players_list = side_data.get("players", [])

        for item in players_list:

            player = item.get("player", {})

            if not player:
                continue

            # =====================================
            # TEAM
            # =====================================

            team_id = item.get("teamId")

            # Skip invalid

            if team_id is None:
                continue

            # =====================================
            # PLAYER
            # =====================================

            player_id = player.get("id")

            if player_id is None:
                continue

            # =====================================
            # STARTER
            # =====================================

            substitute = item.get("substitute", False)

            starter = not substitute

            # =====================================
            # LINEUP OBJECT
            # =====================================

            lineup_data = {
                # =====================
                # MATCH
                # =====================
                "match_id": match_id,
                # =====================
                # TEAM
                # =====================
                "team_id": team_id,
                # =====================
                # PLAYER
                # =====================
                "player_id": player_id,
                "player_name": player.get("name"),
                # =====================
                # LINEUP INFO
                # =====================
                "starter": starter,
                "substitute": substitute,
                "position": item.get("position"),
                "shirt_number": item.get("jerseyNumber"),
                "captain": item.get("captain", False),
                "formation": formation,
                "side": side,
            }

            lineups.append(lineup_data)

# =====================================
# DATAFRAME
# =====================================

df = pd.DataFrame(lineups)

print(f"\nTotal linhas: {len(df)}")

# =====================================
# EMPTY CHECK
# =====================================

if df.empty:

    raise ValueError("Nenhum lineup encontrado.")

# =====================================
# REMOVE DUPLICATES
# =====================================

df = df.drop_duplicates(subset=["match_id", "team_id", "player_id"])

# =====================================
# REMOVE NULLS
# =====================================

df = df.dropna(subset=["match_id", "team_id", "player_id"])

# =====================================
# SORT
# =====================================

df = df.sort_values(["match_id", "team_id", "starter"], ascending=[True, True, False])

# =====================================
# RESET INDEX
# =====================================

df = df.reset_index(drop=True)

# =====================================
# TYPES
# =====================================

df["match_id"] = df["match_id"].astype("int64")

df["team_id"] = df["team_id"].astype("int64")

df["player_id"] = df["player_id"].astype("int64")

df["starter"] = df["starter"].astype("bool")

df["substitute"] = df["substitute"].astype("bool")

df["side"] = df["side"].astype("category")

df["position"] = df["position"].astype("category")

# =====================================
# SAVE PARQUET
# =====================================

output_file = PROCESSED_PATH / "lineups.parquet"

df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

# =====================================
# LOG
# =====================================

print("\n================================")
print("TRANSFORM LINEUPS FINALIZADO")
print("================================")

print(f"Arquivo salvo em: {output_file}")

print(f"Total registros: {len(df)}")

print("\nSchema:\n")

print(df.dtypes)
