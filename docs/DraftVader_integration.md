# SIMDaddy × DraftVader Pages (Blueprint)

This patch adds a Flask blueprint that mounts several pages powered by data/files from your DraftVader repo.

## Routes

- `/dv/schedules?year=2025` — shows `nfl_schedule_2025.csv`
- `/dv/rookies` — shows `rookie_rankings.csv` (drop this file into `data_files/`)
- `/dv/projections` — offline fallback view using `top_320_players.csv`
- `/dv/transactions?month=YYYYMM` — looks for `transactions_YYYYMM.csv` in `data_files/`
- `/dv/age-curve` — applies age curve to latest `nfl_player_stats_*.csv` (2024→2022)
- `/dv/spike-week?weekly=/path/to.csv` — computes spike week scores from a weekly per-game PPR file

## Installation

1) Copy the `app/dv`, `app/templates/dv`, and `app/static/dv.css` into your SIMDaddy project.
2) Ensure your DraftVader `data_files/` folder is available locally.
   - Preferred: set an environment variable `DV_DATA_DIR` to the absolute path of `data_files/`.
   - Or place `DraftVader-master/data_files/` alongside your SIMDaddy project root.
3) Register the blueprint in your Flask app entry:
   ```python
   # app/__init__.py or app.py
   from app.dv import dv_bp
   app.register_blueprint(dv_bp, url_prefix="/dv")
   ```
4) Visit `/dv/schedules`, `/dv/age-curve`, etc.

## Weekly PPR input for Spike Week
Provide a CSV with columns:
- `player` or `player_display_name`
- `fantasy_points_ppr` (preferred) or `ppr_pts`

You can pass a file path in the query string:
`/dv/spike-week?weekly=C:\\path\\to\\wr_weekly_summary_01.csv`
Or drop a file named `wr_weekly_summary_01.csv` in `data_files/`.