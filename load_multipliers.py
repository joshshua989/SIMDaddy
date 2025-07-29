
# load_multipliers.py

import pandas as pd
from pathlib import Path

MULTIPLIER_CSV_PATHS = {
    "team_script_response": "DATA/multipliers/team_script_response.csv",
    "pace_multiplier": "DATA/multipliers/pace_multiplier.csv",
    "pace_multiplier_weekly": "DATA/multipliers/pace_multiplier_weekly.csv",  # optional
    "def_pass_rate_allowed": "DATA/multipliers/def_pass_rate_allowed.csv",
    "def_pressure_rate_allowed": "DATA/multipliers/def_pressure_rate_allowed.csv",
    "qb_script_response": "DATA/multipliers/qb_script_response.csv",
    "qb_aggressiveness": "DATA/multipliers/qb_aggressiveness.csv",
    "wr_script_sensitivity": "DATA/multipliers/wr_script_sensitivity.csv",
    "wr_target_competition": "DATA/multipliers/wr_target_competition.csv",
    "wr_air_yards_share": "DATA/multipliers/wr_air_yards_share.csv",
    "wr_injury_status": "DATA/multipliers/wr_injury_status.csv"
}

def load_multiplier_csv(path, key_col, value_col, multi_key=False):
    df = pd.read_csv(path, quotechar='"', encoding='utf-8')
    d = {}
    if multi_key:
        for _, row in df.iterrows():
            d[(row[key_col[0]], row[key_col[1]])] = row[value_col]
    else:
        for _, row in df.iterrows():
            d[row[key_col]] = row[value_col]
    return d

def load_all_multipliers():
    result = {}
    for key, file_path in MULTIPLIER_CSV_PATHS.items():
        csv_file = Path(file_path)
        if not csv_file.exists():
            print(f"⚠️ Missing multiplier file: {csv_file}")
            continue
        if key == "pace_multiplier_weekly":
            result[key] = load_multiplier_csv(csv_file, ["Week", "Team"], "Value", multi_key=True)
        else:
            # CORRECTED colmap
            colmap = {
                "team_script_response": ("Team", "Value"),
                "pace_multiplier": ("Key", "Value"),
                "def_pass_rate_allowed": ("Key", "Value"),
                "def_pressure_rate_allowed": ("Team", "Value"),
                "qb_script_response": ("Player", "Value"),
                "qb_aggressiveness": ("Player", "Value"),
                "wr_script_sensitivity": ("Player", "Value"),
                "wr_target_competition": ("Player", "Value"),
                "wr_air_yards_share": ("Player", "Value"),
                "wr_injury_status": ("Player", "Value"),
            }
            k, v = colmap.get(key, (None, None))
            result[key] = load_multiplier_csv(csv_file, k, v)
    return result

