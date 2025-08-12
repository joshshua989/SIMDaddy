# app/dv/dv_data.py

import os
from pathlib import Path
import pandas as pd

# ------------------------------------------------------------
# Candidate locations for DraftVader data_files directory
# ------------------------------------------------------------
def _candidate_data_dirs():
    here = Path(__file__).resolve()
    app_root = here.parents[2]  # SIMDaddy/
    return [
        Path(os.getenv("DV_DATA_DIR")) if os.getenv("DV_DATA_DIR") else None,
        Path(os.getenv("SIMDADDY_DATA_DIR")) if os.getenv("SIMDADDY_DATA_DIR") else None,
        app_root / "DATA",                              # ✅ default (your setup)
        here.parents[2] / "data_files",                 # legacy local
        here.parents[3] / "DraftVader" / "data_files",  # legacy clones
        here.parents[3] / "DraftVader-master" / "data_files",
        Path.cwd() / "DraftVader" / "data_files",
        Path.cwd() / "DraftVader-master" / "data_files",
    ]

def get_data_dir() -> Path:
    tried = []
    for p in _candidate_data_dirs():
        if p is None:
            continue
        tried.append(str(p))
        if p.exists():
            return p
    raise FileNotFoundError(
        "Could not locate DraftVader data_files directory. "
        "Set DV_DATA_DIR or SIMDADDY_DATA_DIR, or put CSVs under SIMDaddy/DATA. "
        f"Tried: {', '.join(tried)}"
    )

def _read_csv(name: str) -> pd.DataFrame:
    data_dir = get_data_dir()
    path = data_dir / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required CSV: {path}\n"
            f"(Resolved data dir: {data_dir})"
        )
    return pd.read_csv(path)

# ------------------------------------------------------------
# Data loaders
# ------------------------------------------------------------
def load_schedule(year: int = 2025) -> pd.DataFrame:
    return _read_csv(f"nfl_schedule_{year}.csv")

def load_top_players() -> pd.DataFrame:
    return _read_csv("top_320_players.csv")

def load_player_stats(year: int) -> pd.DataFrame:
    return _read_csv(f"nfl_player_stats_{year}.csv")

def load_rookie_rankings() -> pd.DataFrame:
    # Optional file; return empty df if missing
    try:
        return _read_csv("rookie_rankings.csv")
    except FileNotFoundError:
        return pd.DataFrame()

# ------------------------------------------------------------
# Age curve logic (multi-pos curve; preserves original columns)
# ------------------------------------------------------------
def apply_age_curve(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds:
      - age_curve_multiplier (float)
      - age_risk_tag (str)

    Robust to column variants:
      - position column: 'pos' or 'position'
      - age column: 'age' or 'player_age'
    """
    if df is None or len(df) == 0:
        return df

    pos_col = "pos" if "pos" in df.columns else ("position" if "position" in df.columns else None)
    age_col = "age" if "age" in df.columns else ("player_age" if "player_age" in df.columns else None)

    if pos_col is None or age_col is None:
        return df

    def get_age_curve_multiplier(pos, age):
        if pd.isna(age):
            return 1.0
        try:
            age = int(age)
        except Exception:
            return 1.0
        pos = (pos or "").upper()
        if pos in ("RB", "FB"):
            if age <= 22: return 1.10
            elif 23 <= age <= 24: return 1.08
            elif 25 <= age <= 27: return 1.03
            elif 28 <= age <= 30: return 0.98
            elif 31 <= age <= 33: return 0.92
            else: return 0.85
        elif pos == "WR":
            if age <= 22: return 1.08
            elif 23 <= age <= 24: return 1.05
            elif 25 <= age <= 28: return 1.02
            elif 29 <= age <= 31: return 0.98
            elif 32 <= age <= 34: return 0.93
            else: return 0.88
        elif pos == "TE":
            if age <= 22: return 1.05
            elif 23 <= age <= 26: return 1.03
            elif 27 <= age <= 30: return 1.00
            elif 31 <= age <= 33: return 0.95
            else: return 0.90
        elif pos == "QB":
            if age <= 22: return 1.00
            elif 23 <= age <= 25: return 1.02
            elif 26 <= age <= 32: return 1.03
            elif 33 <= age <= 36: return 1.02
            elif 37 <= age <= 38: return 1.00
            elif 39 <= age <= 40: return 0.98
            elif 41 <= age <= 44: return 0.95
            else: return 0.90
        else:
            return 1.0

    def get_age_tag(pos, age):
        if pd.isna(age):
            return "Unknown"
        try:
            age = int(age)
        except Exception:
            return "Unknown"
        pos = (pos or "").upper()
        if pos in ("RB", "FB"):
            if age <= 22: return "Breakout Window"
            elif 23 <= age <= 27: return "Prime"
            elif 28 <= age <= 30: return "Late Prime"
            else: return "Decline"
        elif pos == "WR":
            if age <= 22: return "Breakout Window"
            elif 23 <= age <= 28: return "Prime"
            elif 29 <= age <= 31: return "Late Prime"
            else: return "Decline"
        elif pos == "TE":
            if age <= 22: return "Development"
            elif 23 <= age <= 30: return "Prime"
            else: return "Decline"
        elif pos == "QB":
            if age <= 22: return "Development"
            elif 23 <= age <= 38: return "Prime"
            else: return "Decline"
        return "Unknown"

    out = df.copy()
    out["age_curve_multiplier"] = out[[pos_col, age_col]].apply(lambda r: get_age_curve_multiplier(r.iloc[0], r.iloc[1]), axis=1)
    out["age_risk_tag"] = out[[pos_col, age_col]].apply(lambda r: get_age_tag(r.iloc[0], r.iloc[1]), axis=1)
    return out

# ------------------------------------------------------------
# Spike week from weekly data (expects per-game PPR)
# ------------------------------------------------------------
def compute_spike_week(weekly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expects columns:
      - 'player' or 'player_display_name'
      - 'fantasy_points_ppr' (preferred) OR 'ppr_pts'
    Returns a DataFrame with boom/bust counts and Spike Week Score.
    """
    name_col = "player_display_name" if "player_display_name" in weekly_df.columns else "player"
    ppr_col = "fantasy_points_ppr" if "fantasy_points_ppr" in weekly_df.columns else ("ppr_pts" if "ppr_pts" in weekly_df.columns else None)
    if not ppr_col:
        raise ValueError("Weekly DF must include 'fantasy_points_ppr' or 'ppr_pts' column.")

    df = weekly_df[[name_col, ppr_col]].rename(columns={name_col:"player_name", ppr_col:"ppr"}).copy()
    total = df.groupby("player_name").size().rename("total_games")

    def over(t): return (df[df["ppr"] > t].groupby("player_name").size().rename(f"over_{t}_ppr_count"))
    def under(t): return (df[df["ppr"] < t].groupby("player_name").size().rename(f"under_{t}_ppr_count"))

    merged = pd.concat([total, over(20), over(25), over(30), under(5), under(10), under(15)], axis=1).fillna(0)
    merged = merged.reset_index()

    merged["boom_score"] = merged["over_20_ppr_count"]*1 + merged["over_25_ppr_count"]*2 + merged["over_30_ppr_count"]*3
    merged["bust_score"] = merged["under_5_ppr_count"]*2 + merged["under_10_ppr_count"]*1.5 + merged["under_15_ppr_count"]*1
    merged["spike_week_score"] = merged["boom_score"] - merged["bust_score"]

    merged = merged.sort_values("spike_week_score", ascending=False)
    return merged
