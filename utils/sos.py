# utils/sos.py
from pathlib import Path
import pandas as pd

def load_sos(data_dir: Path, position: str = "WR"):
    '''
    Builds a team-level defensive SoS index for a position using available CSVs.
    Returns columns: opponent_team, sos_index, games
    '''
    data_dir = Path(data_dir)
    sources = [
        "nfl_player_stats_2024.csv",
        "nfl_player_stats_2023.csv",
        "nfl_player_stats_2022.csv",
        "wr_weekly_summary_01.csv",
        "weekly_ppr.csv",
    ]
    paths = [data_dir/p for p in sources if (data_dir/p).exists()]
    if not paths:
        return None

    frames = []
    for p in paths:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue

        cols = {c.lower(): c for c in df.columns}
        team_col = cols.get("team") or cols.get("posteam") or cols.get("home_team")
        opp_col  = cols.get("opponent") or cols.get("defteam") or cols.get("away_team") or cols.get("opp")
        yds_col  = cols.get("receiving_yards") or cols.get("rec_yds") or cols.get("yards") or cols.get("fantasy_points_ppr")
        if not (team_col and opp_col and yds_col):
            continue

        tmp = df[[team_col, opp_col, yds_col]].rename(columns={team_col:"team", opp_col:"opp", yds_col:"metric"})
        frames.append(tmp)

    if not frames:
        return None

    data = pd.concat(frames, ignore_index=True)
    sos = (data.groupby("opp")["metric"].mean()
                 .rename("allowed_metric")
                 .reset_index()
                 .rename(columns={"opp":"opponent_team"}))

    mean = sos["allowed_metric"].mean()
    sos["sos_index"] = 100.0 * sos["allowed_metric"] / mean
    sos["games"] = data.groupby("opp").size().values
    return sos[["opponent_team","sos_index","games"]]
