from flask import render_template, current_app, request, flash
from . import dv_bp
from .dv_data import (
    load_schedule, load_top_players, load_player_stats, load_rookie_rankings,
    apply_age_curve, compute_spike_week, get_data_dir
)
import pandas as pd
from pathlib import Path

@dv_bp.context_processor
def inject_dv_defaults():
    return {"dv_data_dir": str(get_data_dir())}

@dv_bp.route("/schedules")
def schedules():
    year = int(request.args.get("year", 2025))
    try:
        df = load_schedule(year)
    except Exception as e:
        flash(str(e), "error")
        df = pd.DataFrame()
    return render_template("dv/schedules.html", year=year, table=df.to_dict(orient="records"), columns=list(df.columns) if not df.empty else [])

@dv_bp.route("/rookies")
def rookies():
    df = load_rookie_rankings()
    if df.empty:
        flash("rookie_rankings.csv not found in DraftVader data_files. Drop one in to populate this page.", "warning")
    return render_template("dv/rookies.html", table=df.to_dict(orient="records"), columns=list(df.columns) if not df.empty else [])

@dv_bp.route("/projections")
def projections():
    # Offline fallback: show top_320_players.csv as pseudo projections
    try:
        df = load_top_players()
    except Exception as e:
        flash(str(e), "error")
        df = pd.DataFrame()
    return render_template("dv/projections.html", table=df.to_dict(orient="records"), columns=list(df.columns) if not df.empty else [])

@dv_bp.route("/transactions")
def transactions():
    # This route expects a local CSV 'transactions_YYYYMM.csv' if scraping isn't available.
    # If you have live scraping, wire it in your main app's background job and drop CSVs here.
    month = request.args.get("month")  # format YYYYMM
    df = pd.DataFrame()
    if month:
        csv_name = f"transactions_{month}.csv"
        path = Path(get_data_dir()) / csv_name
        if path.exists():
            df = pd.read_csv(path)
        else:
            flash(f"Couldn't find {csv_name} in data_files. Provide a local export or enable scraper.", "warning")
    else:
        flash("Add ?month=YYYYMM to the URL to view a local transactions CSV export (e.g., /dv/transactions?month=202507).", "info")
    return render_template("dv/transactions.html", month=month, table=df.to_dict(orient="records"), columns=list(df.columns) if not df.empty else [])

@dv_bp.route("/age-curve")
def age_curve():
    # Apply to latest season player stats if available, else to top_320
    df = pd.DataFrame()
    for year in (2024, 2023, 2022):
        try:
            df = load_player_stats(year)
            break
        except Exception:
            continue
    if df.empty:
        try:
            df = load_top_players()
        except Exception as e:
            flash(str(e), "error")
            return render_template("dv/age_curve.html", table=[], columns=[])

    out = apply_age_curve(df)
    return render_template("dv/age_curve.html", table=out.to_dict(orient="records"), columns=list(out.columns))

@dv_bp.route("/spike-week")
def spike_week():
    """
    Compute spike week metrics from a weekly per-game PPR file.
    Provide one of:
      - ?weekly=/absolute/path.csv
      - Place a file named 'wr_weekly_summary_01.csv' or 'weekly_ppr.csv' into data_files
    """
    weekly_param = request.args.get("weekly")
    weekly_df = None
    candidates = []
    if weekly_param:
        candidates.append(Path(weekly_param))
    # fallback names
    candidates += [Path(get_data_dir()) / n for n in ("wr_weekly_summary_01.csv", "weekly_ppr.csv")]

    for p in candidates:
        if p.exists():
            try:
                weekly_df = pd.read_csv(p)
                break
            except Exception:
                continue

    if weekly_df is None:
        flash("Need a weekly per-game PPR CSV (columns: player or player_display_name and fantasy_points_ppr). "
              "Pass ?weekly=/path/to.csv or drop 'wr_weekly_summary_01.csv' into data_files.", "warning")
        return render_template("dv/spike_week.html", table=[], columns=[])

    try:
        out = compute_spike_week(weekly_df)
    except Exception as e:
        flash(str(e), "error")
        return render_template("dv/spike_week.html", table=[], columns=[])

    return render_template("dv/spike_week.html", table=out.to_dict(orient="records"),
                           columns=list(out.columns))