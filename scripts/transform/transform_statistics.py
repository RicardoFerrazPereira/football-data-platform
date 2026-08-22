import json
from pathlib import Path

import pandas as pd

# =====================================
# CONFIG
# =====================================

RAW_PATH = Path(
    "data/raw/statistics"
)

PROCESSED_PATH = Path(
    "data/processed"
)

PROCESSED_PATH.mkdir(
    parents=True,
    exist_ok=True
)

# =====================================
# FILES
# =====================================

json_files = list(
    RAW_PATH.glob("*.json")
)

print(f"Arquivos encontrados: {len(json_files)}")

# =====================================
# STORAGE
# =====================================

statistics_data = []

# =====================================
# HELPER
# =====================================

def parse_numeric_value(value):

    """
    Convert statistics values to numeric when possible.
    """

    if value is None:
        return None

    # =====================================
    # STRING
    # =====================================

    if isinstance(value, str):

        value = value.strip()

        # Remove %

        value = value.replace("%", "")

        # Remove commas

        value = value.replace(",", "")

        # Empty string

        if value == "":
            return None

    # =====================================
    # TRY CONVERSION
    # =====================================

    try:

        return float(value)

    except:

        return None

# =====================================
# LOOP FILES
# =====================================

for file in json_files:

    match_id = int(file.stem)

    print(f"Lendo: {file.name}")

    with open(file, "r", encoding="utf-8") as f:

        data = json.load(f)

    # =====================================
    # PERIODS
    # =====================================

    periods = data.get("statistics", [])

    for period in periods:

        period_name = period.get("period")

        groups = period.get("groups", [])

        # =====================================
        # GROUPS
        # =====================================

        for group in groups:

            group_name = group.get("groupName")

            statistics_items = group.get(
                "statisticsItems",
                []
            )

            # =====================================
            # STATISTICS
            # =====================================

            for item in statistics_items:

                statistic_name = item.get("name")

                home_value = item.get("home")

                away_value = item.get("away")

                # =====================================
                # HOME
                # =====================================

                statistics_data.append({

                    "match_id": match_id,

                    "period": period_name,

                    "group_name": group_name,

                    "statistic_name": statistic_name,

                    "team_side": "home",

                    "value": home_value,

                    "value_numeric": (
                        parse_numeric_value(
                            home_value
                        )
                    )
                })

                # =====================================
                # AWAY
                # =====================================

                statistics_data.append({

                    "match_id": match_id,

                    "period": period_name,

                    "group_name": group_name,

                    "statistic_name": statistic_name,

                    "team_side": "away",

                    "value": away_value,

                    "value_numeric": (
                        parse_numeric_value(
                            away_value
                        )
                    )
                })

# =====================================
# DATAFRAME
# =====================================

df = pd.DataFrame(statistics_data)

print(
    f"\nTotal linhas antes deduplicação: {len(df)}"
)

# =====================================
# REMOVE DUPLICATES
# =====================================

df = df.drop_duplicates()

print(
    f"Total linhas após deduplicação: {len(df)}"
)

# =====================================
# SORT
# =====================================

df = df.sort_values(

    [
        "match_id",
        "period",
        "group_name",
        "statistic_name",
        "team_side"
    ]
)

# =====================================
# RESET INDEX
# =====================================

df = df.reset_index(drop=True)

# =====================================
# OPTIMIZE DTYPES
# =====================================

df["match_id"] = df["match_id"].astype(
    "int64"
)

df["team_side"] = df[
    "team_side"
].astype("category")

# =====================================
# SAVE PARQUET
# =====================================

output_file = (
    PROCESSED_PATH / "statistics.parquet"
)

df.to_parquet(

    output_file,

    engine="pyarrow",

    compression="snappy",

    index=False
)

# =====================================
# LOG
# =====================================

print("\n================================")
print("TRANSFORM STATISTICS FINALIZADO")
print("================================")

print(f"Arquivo salvo em: {output_file}")

print(f"Total registros: {len(df)}")

print("\nSchema:\n")

print(df.dtypes)