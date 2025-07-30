
# views/routes.py

from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from flask_login import current_user
import os
import pandas as pd
from utils.injury_reports import get_injury_reports


views_bp = Blueprint('views', __name__)
DATA_DIR = 'DATA/sim_results'

TEAM_COLORS = {
    "CIN": "#FB4F14",
    "DET": "#0076B6",
    "PHI": "#004C54",
    "DAL": "#041E42",
    "BUF": "#00338D",
    # ...add all as needed
}

# --- LANDING PAGE ---
@views_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    return render_template("landing.html")


# --- DECORATOR FOR SESSION-BASED LOGIN ---
def require_login(func):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# --- HOME PAGE (CHANGE TO /home) ---
@views_bp.route('/home')
@require_login
def home():
    weeks = sorted([int(f.split('_')[1].split('.')[0]) for f in os.listdir(DATA_DIR) if f.startswith('week_') and f.endswith('.csv')])
    return render_template('index.html', weeks=weeks, username=session.get('user'))


# --- WEEK VIEW ---
@views_bp.route('/week/<int:week>')
@require_login
def week_view(week):
    fname = f'week_{week:02d}.csv'
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        flash(f"No data for week {week}", "warning")
        return redirect(url_for('views.home'))

    df = pd.read_csv(path)
    rows = df.to_dict(orient='records')
    for row in rows:
        row['team_color'] = TEAM_COLORS.get(row['team'], "#444")
        row['bg_color'] = matchup_bg_color(row['adj_pts'])
    return render_template('week.html', week=week, rows=rows)


# --- MATCHUP COLOR HELPER ---
def matchup_bg_color(adj_pts):
    try:
        adj_pts = float(adj_pts)
        if adj_pts >= 18: return "#24d35d"
        elif adj_pts >= 15: return "#ffdf5b"
        else: return "#ef6161"
    except:
        return "#bbb"


@views_bp.route("/injuries")
@require_login
def injuries():
    print("Fetching injuries...")
    df = get_injury_reports()

    if df is None or df.empty:
        flash("No injury data available right now.", "warning")
        return render_template("injuries.html", injuries=[])

    injuries_list = df.to_dict(orient="records")
    return render_template("injuries.html", injuries=injuries_list)
