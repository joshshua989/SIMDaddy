
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = {
    "NFL_SCHEDULE_2025.csv": ["Week", "Date", "Home", "Visitor", "Time", "ProjectedHomeScore", "ProjectedAwayScore"],
    "WR_STATS_2024.csv": [
        "player_id", "full_name", "team", "slot_snap_rate",
        "fp_per_target_vs_man", "fp_per_target_vs_zone",
        "routes_vs_man", "routes_vs_zone"
    ],
    "DB_STATS_2022_2023_2024.csv": [
        "week", "team", "player_id", "position", "adj_fp",
        "targets_allowed", "routes_defended", "coverage_rating"
    ],
    "DEF_TEAM_COVERAGE_TAGS.csv": ["week", "team", "man_coverage_rate", "zone_coverage_rate"],
    "STADIUM_ENVIRONMENT_PROFILES.csv": ["Team", "Latitude", "Longitude", "TurfType", "HumidityControl"],
    "wr_prop_market.csv": ["player", "market", "value"],
    "roster_2025.csv": ["team", "position", "depth_chart_position", "full_name", "gsis_id"],
    "roster_2024.csv": ["team", "position", "depth_chart_position", "full_name", "gsis_id"],
}

def validate_csv_columns(base_dir="DATA"):
    issues = []
    for file, required_cols in REQUIRED_COLUMNS.items():
        file_path = Path(base_dir) / file if not file.startswith("roster") else Path(file)
        if not file_path.exists():
            issues.append(f"❌ Missing file: {file}")
            continue
        try:
            df = pd.read_csv(file_path)
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                issues.append(f"⚠️ {file} is missing columns: {', '.join(missing)}")
            else:
                print(f"✅ {file} passed.")
        except Exception as e:
            issues.append(f"❌ Error reading {file}: {e}")
    return issues

if __name__ == "__main__":
    problems = validate_csv_columns()
    if problems:
        print("\n".join(problems))
    else:
        print("✅ All input files passed validation.")
