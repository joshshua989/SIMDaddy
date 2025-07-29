
# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import os
import json

app = Flask(__name__)
app.secret_key = 'SUPER_SECRET_CHANGE_THIS_KEY'  # Change in production!

DATA_DIR = 'DATA/sim_results'
USERS_FILE = 'users.json'  # Store user credentials (hashed for prod!)

TEAM_COLORS = {
    "CIN": "#FB4F14",
    "DET": "#0076B6",
    "PHI": "#004C54",
    "DAL": "#041E42",
    "BUF": "#00338D",
    # ...add all as needed
}
def matchup_bg_color(adj_pts):
    try:
        adj_pts = float(adj_pts)
        if adj_pts >= 18:    # green
            return "#24d35d"
        elif adj_pts >= 15:  # yellow
            return "#ffdf5b"
        else:                # red
            return "#ef6161"
    except:
        return "#bbb"

def matchup_color(score):
    try:
        score = float(score)
        if score >= 2.4: return "#24d35d"
        elif score >= 2.1: return "#ffdf5b"
        else: return "#ef6161"
    except: return "#bbb"

# ---- Auth ----
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def check_login(username, password):
    users = load_users()
    # For demo, plain text; hash for real!
    return users.get(username) == password

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        if check_login(user, pw):
            session['user'] = user
            return redirect(url_for('home'))
        flash("Login failed.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

def require_login(func):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# ---- Main Views ----
@app.route('/')
@require_login
def home():
    weeks = sorted([int(f.split('_')[1].split('.')[0]) for f in os.listdir(DATA_DIR) if f.startswith('week_') and f.endswith('.csv')])
    return render_template('index.html', weeks=weeks, username=session.get('user'))

def penalty_color(val):
    # Green if >= 0.98, yellow for 0.93-0.98, red < 0.93
    try:
        val = float(val)
        if val >= 0.98:
            return "#24d35d"
        elif val >= 0.93:
            return "#ffdf5b"
        else:
            return "#ef6161"
    except:
        return "#bbb"

@app.route('/week/<int:week>')
@require_login
def week_view(week):
    fname = f'week_{week:02d}.csv'
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        flash(f"No data for week {week}", "warning")
        return redirect(url_for('home'))
    df = pd.read_csv(path)
    rows = df.to_dict(orient='records')
    for row in rows:
        row['team_color'] = TEAM_COLORS.get(row['team'], "#444")
        row['bg_color'] = matchup_bg_color(row['adj_pts'])
    return render_template('week.html', week=week, rows=rows)

# ---- Static files (css/js/images) ----
@app.route('/static/<path:path>')
def send_static(path):
    return app.send_static_file(path)

if __name__ == "__main__":
    app.run(debug=True)
