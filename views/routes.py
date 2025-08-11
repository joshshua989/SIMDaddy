# views/routes.py

from flask import Blueprint, render_template, session, redirect, url_for, request, flash, current_app, abort
from flask_login import login_required, current_user
import os, sys, subprocess, time
from pathlib import Path
import pandas as pd

from utils.injury_reports import get_injury_reports
from config import NFL_SCHEDULE_2025_FILE, STADIUM_ENV_FILE
from utils.team_lookup import infer_team_code
from utils.team_logo import team_logo_url  # <-- uses infer_team_code under the hood

# Wallet/entitlement helpers
from services.wallet import (
    get_or_create_wallet, earn_coins, spend_coins, add_rep,
    grant_entitlement, has_entitlement
)
from models.wallet import Wallet, CoinTxn, RepEvent, Entitlement

# NEW: product pricing config
from config import get_week_product, get_season_product

views_bp = Blueprint('views', __name__)

# Where weekly CSV outputs land for the dashboard (adjust if yours differs)
DATA_DIR = 'DATA/sim_results'

TEAM_COLORS = {
    "CIN": "#FB4F14", "DET": "#0076B6", "PHI": "#004C54", "DAL": "#041E42", "BUF": "#00338D",
    # ...add all as needed
}

# ----- Logo helpers -----
NFL_LOGO_CDN = "https://a.espncdn.com/i/teamlogos/nfl/500/{}"  # expects like "det.png"
TEAM_NAME_TO_ABBR = {
    "49ers":"sf","San Francisco":"sf",
    "Bears":"chi","Chicago":"chi",
    "Bengals":"cin","Cincinnati":"cin",
    "Bills":"buf","Buffalo":"buf",
    "Broncos":"den","Denver":"den",
    "Browns":"cle","Cleveland":"cle",
    "Buccaneers":"tb","Tampa Bay":"tb","Tampa":"tb",
    "Cardinals":"ari","Arizona":"ari",
    "Chargers":"lac","Los Angeles Chargers":"lac","LA Chargers":"lac",
    "Chiefs":"kc","Kansas City":"kc",
    "Colts":"ind","Indianapolis":"ind",
    "Commanders":"wsh","Washington":"wsh",
    "Cowboys":"dal","Dallas":"dal",
    "Dolphins":"mia","Miami":"mia",
    "Eagles":"phi","Philadelphia":"phi",
    "Falcons":"atl","Atlanta":"atl",
    "Giants":"nyg","New York Giants":"nyg",
    "Jaguars":"jac","Jacksonville":"jac",
    "Jets":"nyj","New York Jets":"nyj",
    "Lions":"det","Detroit":"det",
    "Packers":"gb","Green Bay":"gb",
    "Panthers":"car","Carolina":"car",
    "Patriots":"ne","New England":"ne",
    "Raiders":"lv","Las Vegas":"lv",
    "Rams":"lar","Los Angeles Rams":"lar","LA Rams":"lar",
    "Ravens":"bal","Baltimore":"bal",
    "Saints":"no","New Orleans":"no",
    "Seahawks":"sea","Seattle":"sea",
    "Steelers":"pit","Pittsburgh":"pit",
    "Texans":"hou","Houston":"hou",
    "Titans":"ten","Tennessee":"ten",
    "Vikings":"min","Minnesota":"min",
}
def infer_team_abbr(text: str | None) -> str | None:
    if not text:
        return None
    low = text.lower()
    for k, abbr in TEAM_NAME_TO_ABBR.items():
        if k.lower() in low:
            return abbr
    return None

def team_logo_url(text: str | None) -> str | None:
    abbr = infer_team_abbr(text)
    return NFL_LOGO_CDN.format(f"{abbr}.png") if abbr else None

# ----- Common helpers -----
def matchup_bg_color(adj_pts):
    try:
        adj_pts = float(adj_pts)
        if adj_pts >= 18: return "#24d35d"
        elif adj_pts >= 15: return "#ffdf5b"
        else: return "#ef6161"
    except:
        return "#bbb"

# =========================
#          ROUTES
# =========================

# Landing page
@views_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    return render_template("landing.html")

# Session-based guard (kept)
def require_login(func):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Home (dashboard)
@views_bp.route('/home')
@require_login
def home():
    weeks = sorted([
        int(f.split('_')[1].split('.')[0])
        for f in os.listdir(DATA_DIR)
        if f.startswith('week_') and f.endswith('.csv')
    ])
    # ensure wallet exists so balances always render
    if current_user.is_authenticated:
        get_or_create_wallet(current_user.id)
    return render_template('index.html', weeks=weeks, username=session.get('user'))

# Week view (now gated by entitlement)
@views_bp.route('/week/<int:week>')
@require_login
def week_view(week):
    # Entitlement key for the week
    key = f"2025-W{week:02d}"

    # If the user has the week or a season pass, let them in
    unlocked = False
    if current_user.is_authenticated:
        unlocked = has_entitlement(current_user.id, 'week', key) or has_entitlement(current_user.id, 'season', '2025-SEASON')

    if not unlocked:
        # Pricing from config (fallbacks if missing)
        p = get_week_product(2025) or {"coin_price": 200, "usd_price": 2.99}
        COIN_PRICE = p["coin_price"]
        USD_PRICE  = p["usd_price"]
        # Ensure wallet exists to show balance
        w = get_or_create_wallet(current_user.id)
        return render_template('paywall_week.html', week=week, coin_price=COIN_PRICE, usd_price=USD_PRICE, key=key, balance=w.coins_balance)

    # Proceed with the normal rendering (existing logic)
    fname = f'week_{week:02d}.csv'
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        flash(f"No data for week {week}", "warning")
        return redirect(url_for('views.home'))

    df = pd.read_csv(path)
    rows = df.to_dict(orient='records')
    for row in rows:
        row['team_color'] = TEAM_COLORS.get(row.get('team'), "#444")
        row['bg_color'] = matchup_bg_color(row.get('adj_pts'))
    return render_template('week.html', week=week, rows=rows)

# Unlock a week with coins
@views_bp.route('/unlock/week/<int:week>', methods=['POST'])
@login_required
def unlock_week(week):
    key = f"2025-W{week:02d}"

    if has_entitlement(current_user.id, 'week', key):
        return redirect(url_for('views.week_view', week=week))

    p = get_week_product(2025) or {"coin_price": 200}
    COIN_PRICE = p["coin_price"]

    try:
        spend_coins(current_user.id, COIN_PRICE, reason=f"unlock_week:{key}", idem=f"unlock-week-{key}-{current_user.id}")
        grant_entitlement(current_user.id, 'week', key, source='coins')
        flash(f"Week {week} unlocked with 💸 coins!", "success")
        # small rep bump for first unlock
        add_rep(current_user.id, 5, reason=f"unlock_week:{key}")
        return redirect(url_for('views.week_view', week=week))
    except ValueError:
        flash("Not enough 💸 coins. You can purchase more or unlock with cash.", "danger")
        return redirect(url_for('views.week_view', week=week))

# Unlock season with coins
@views_bp.route('/unlock/season/<int:year>', methods=['POST'])
@login_required
def unlock_season(year):
    key = f"{year}-SEASON"

    if has_entitlement(current_user.id, 'season', key):
        return redirect(url_for('views.home'))

    p = get_season_product(year) or {"coin_price": 1800}
    COIN_PRICE = p["coin_price"]

    try:
        spend_coins(current_user.id, COIN_PRICE, reason=f"unlock_season:{key}", idem=f"unlock-season-{key}-{current_user.id}")
        grant_entitlement(current_user.id, 'season', key, source='coins')
        flash(f"Season {year} unlocked with 💸 coins!", "success")
        add_rep(current_user.id, 25, reason=f"unlock_season:{key}")
        return redirect(url_for('views.home'))
    except ValueError:
        flash("Not enough 💸 coins to unlock the season.", "danger")
        return redirect(url_for('views.home'))

# Developer/admin route to grant coins
@views_bp.route('/dev/grant-coins', methods=['POST'])
@login_required
def dev_grant_coins():
    if not getattr(current_user, "is_admin", False):
        abort(403)
    uid = int(request.form['user_id'])
    amt = int(request.form['amount'])
    earn_coins(uid, amt, reason="admin_grant", idem=f"admin-{uid}-{amt}-{int(time.time())}")
    flash(f"Granted {amt} 💰 to user {uid}.", "success")
    return redirect(url_for('views.account'))

@views_bp.route("/injuries", methods=["GET"])
def injuries():
    """
    Load injury reports, attach local logo URLs when possible, and paginate 20/pg.
    """
    df = get_injury_reports()

    if df is None or df.empty:
        flash("No injury data available right now.", "warning")
        return render_template(
            "injuries.html",
            injuries=[],
            total_count=0,
            page=1,
            total_pages=1,
            page_size=20,
            showing_start=0,
            showing_end=0,
        )

    items = df.to_dict(orient="records")
    for it in items:
        text = " ".join(
            s for s in [
                str(it.get("headline", "") or ""),
                str(it.get("description", "") or "")
            ] if s
        )
        try:
            it["logo_url"] = team_logo_url(text)
        except Exception:
            it["logo_url"] = None

    PAGE_SIZE = 20
    page = request.args.get("page", 1, type=int) or 1
    total_count = len(items)
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    items_page = items[start:end]

    try:
        current_app.logger.info(
            "Injuries: total=%d, page=%d/%d, showing=%d-%d",
            total_count, page, total_pages,
            0 if total_count == 0 else start + 1, min(end, total_count)
        )
    except Exception:
        pass

    return render_template(
        "injuries.html",
        injuries=items_page,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
        page_size=PAGE_SIZE,
        showing_start=0 if total_count == 0 else start + 1,
        showing_end=min(end, total_count),
    )

# Account (expanded with wallet + ledgers + milestones)
@views_bp.route("/account")
@login_required
def account():
    # Ensure wallet exists
    w = get_or_create_wallet(current_user.id)

    # Latest transactions & rep events
    coin_txns = (CoinTxn.query
                 .filter_by(user_id=current_user.id)
                 .order_by(CoinTxn.created_at.desc())
                 .limit(20).all())
    rep_events = (RepEvent.query
                  .filter_by(user_id=current_user.id)
                  .order_by(RepEvent.created_at.desc())
                  .limit(20).all())

    ents = (Entitlement.query
            .filter_by(user_id=current_user.id)
            .order_by(Entitlement.created_at.desc())
            .all())

    # Avatar URL (falls back to default in /static/images/)
    default_avatar_path = url_for('static', filename='images/avatar_default.svg')
    avatar_url = (getattr(current_user, "profile_pic_url", None)
                  or getattr(current_user, "avatar_url", None)
                  or default_avatar_path)

    # Display name
    display_name = (getattr(current_user, "first_name", None)
                    or getattr(current_user, "username", None)
                    or getattr(current_user, "email", None))

    # Milestones (display-only for now)
    milestones = [
        {"code":"complete_profile", "title":"Complete your profile",
         "desc":"Fill out name & contact details.",
         "rep":50, "coins":20},
        {"code":"verify_phone", "title":"Verify your phone",
         "desc":"Confirm your SMS number.",
         "rep":25, "coins":10},
        {"code":"first_sim", "title":"Run your first simulation",
         "desc":"Kick off any week simulation.",
         "rep":15, "coins":5},
        {"code":"ten_weeks", "title":"Simulate 10 weeks",
         "desc":"Accumulate ten week runs total.",
         "rep":50, "coins":20},
        {"code":"season_unlock", "title":"Unlock a season",
         "desc":"Unlock any full season with 💸 coins.",
         "rep":25, "coins":0},
        {"code":"daily_streak_7", "title":"7-day streak",
         "desc":"Active on SIMDaddy seven days straight.",
         "rep":30, "coins":30},
        {"code":"bug_report", "title":"Helpful bug report",
         "desc":"Submit a validated bug or fix suggestion.",
         "rep":25, "coins":10},
    ]

    info = {
        "email": getattr(current_user, "email", None),
        "first_name": getattr(current_user, "first_name", None),
        "last_name": getattr(current_user, "last_name", None),
        "created_at": getattr(current_user, "created_at", None),
        "display_name": display_name,
        "avatar_url": avatar_url,
    }
    return render_template("account.html",
                           user=info,
                           wallet=w,
                           coin_txns=coin_txns,
                           rep_events=rep_events,
                           entitlements=ents,
                           milestones=milestones)

# ===== Weather (fixed) =====
def _load_stadium_env_by_team():
    out = {}
    if not os.path.exists(STADIUM_ENV_FILE):
        return out
    try:
        env = pd.read_csv(STADIUM_ENV_FILE)
    except Exception:
        return out

    cols = {c.lower(): c for c in env.columns}
    team_col = cols.get("team") or cols.get("abbr") or cols.get("franchise")
    stadium_col = cols.get("stadium") or cols.get("name")
    roof_col = cols.get("dome") or cols.get("roof") or cols.get("environmenttype")

    for _, r in env.iterrows():
        team_val = (str(r.get(team_col)) if team_col else "").strip().lower()
        if not team_val:
            continue
        stadium = (str(r.get(stadium_col)) if stadium_col else "").strip() or None
        roof = (str(r.get(roof_col)) if roof_col else "").strip().lower()
        is_dome = any(k in roof for k in ["dome","indoor","fixed","retractable-closed","closed"])
        out[team_val] = {"stadium": stadium, "is_dome": is_dome}
    return out

@views_bp.route("/weather")
def weather_insights():
    import csv
    data_path = os.getenv("DATA_DIR", "DATA")

    sched_path = os.path.join(data_path, "nfl_schedules", "NFL_SCHEDULE_2025.csv")
    schedule = []
    if os.path.exists(sched_path):
        sdf = pd.read_csv(sched_path)
        col_week = next((c for c in sdf.columns if c.lower() in ["week","wk"]), None)
        col_home = next((c for c in sdf.columns if c.lower() in ["home","home_team","hometeam","home_team_name"]), None)
        col_away = next((c for c in sdf.columns if c.lower() in ["away","away_team","awayteam","away_team_name"]), None)
        col_date = next((c for c in sdf.columns if "date" in c.lower()), None)
        col_stadium = next((c for c in sdf.columns if "stadium" in c.lower()), None)
        if col_week and col_home:
            for _, r in sdf.iterrows():
                try:
                    wk = int(r.get(col_week))
                except Exception:
                    continue
                schedule.append({
                    "week": wk,
                    "home": (str(r.get(col_home)) or "").strip(),
                    "away": (str(r.get(col_away)) or "").strip() if col_away else "",
                    "date": str(r.get(col_date)) if col_date else "",
                    "stadium": (str(r.get(col_stadium)) or "").strip() if col_stadium else "",
                })

    weeks_all = sorted({g["week"] for g in schedule}) if schedule else list(range(1,19))
    week_sel = request.args.get("week", type=int) or (weeks_all[0] if weeks_all else 1)
    games = [g for g in schedule if g["week"] == week_sel]

    seen_home = set()
    games_dedup = []
    for g in games:
        h = g["home"].lower()
        if h and h not in seen_home:
            seen_home.add(h)
            games_dedup.append(g)

    wx_candidates = [
        os.path.join(os.getcwd(), "weather_log.csv"),
        os.path.join(data_path, "weather_log.csv"),
    ]
    log_path = next((p for p in wx_candidates if os.path.exists(p)), None)
    wx_map = {}
    if log_path:
        try:
            wdf = pd.read_csv(log_path)
            for _, r in wdf.iterrows():
                wk = r.get("week")
                st = str(r.get("stadium") or "").strip().lower()
                wx_map[(int(wk), st)] = {
                    "shortForecast": r.get("shortForecast"),
                    "temperature": r.get("temperature"),
                    "windSpeed": r.get("windSpeed"),
                    "precipitation": r.get("precipitation"),
                    "weather_boost": r.get("weather_boost"),
                    "game_date": r.get("game_date"),
                }
        except Exception:
            pass

    env_map = {}
    env_candidates = [
        os.path.join(os.getcwd(), "STADIUM_ENVIRONMENT_PROFILES.csv"),
        os.path.join(data_path, "STADIUM_ENVIRONMENT_PROFILES.csv"),
    ]
    env_path = next((p for p in env_candidates if os.path.exists(p)), None)
    if env_path:
        try:
            with open(env_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = (row.get("Stadium") or row.get("Name") or "").strip()
                    roof = (row.get("Roof") or row.get("EnvironmentType") or row.get("Dome") or "").strip().lower()
                    if not name:
                        continue
                    is_dome = any(k in roof for k in ["dome","indoor","fixed","retractable-closed","closed"])
                    env_map[name.lower()] = "Dome/Indoor" if is_dome else "Open Air"
        except Exception:
            env_map = {}

    TEAM_ABBR = {
        "49ers":"sf","san francisco 49ers":"sf","san francisco":"sf",
        "bears":"chi","chicago bears":"chi","chicago":"chi",
        "bengals":"cin","bills":"buf","broncos":"den","browns":"cle","buccaneers":"tb","tampa bay":"tb",
        "cardinals":"ari","chargers":"lac","chiefs":"kc","colts":"ind","commanders":"wsh",
        "cowboys":"dal","dolphins":"mia","eagles":"phi","falcons":"atl","giants":"nyg","jaguars":"jac",
        "jets":"nyj","lions":"det","packers":"gb","panthers":"car","patriots":"ne","raiders":"lv",
        "rams":"lar","ravens":"bal","saints":"no","seahawks":"sea","steelers":"pit","texans":"hou",
        "titans":"ten","vikings":"min",
    }
    def logo_url(team_name):
        if not team_name: return None
        t = team_name.strip().lower()
        abbr = TEAM_ABBR.get(t) or TEAM_ABBR.get(t.replace(" ", ""))
        if not abbr:
            last = t.split()[-1]
            abbr = TEAM_ABBR.get(last)
        return f"https://a.espncdn.com/i/teamlogos/nfl/500/{abbr}.png" if abbr else None

    def fmt_temp(v):
        try: return f"{int(float(str(v).split()[0]))}°F"
        except: return "—"
    def fmt_wind(v):
        s = str(v or "").strip()
        num = "".join(ch for ch in s if ch.isdigit() or ch == ".")
        return f"{int(float(num))} mph" if num else "—"
    def fmt_precip(v):
        try: return f"{int(round(float(str(v).replace('%','').strip())))}%"
        except: return "—"

    rows = []
    for g in games_dedup:
        st = (g["stadium"] or "").strip()
        st_key = (week_sel, st.lower())
        wx = wx_map.get(st_key, {})
        env = env_map.get(st.lower(), "Open Air")
        rows.append({
            "week": g["week"],
            "home": g["home"],
            "away": g["away"],
            "stadium": st,
            "env": env,
            "game_date": wx.get("game_date") or g["date"],
            "forecast": wx.get("shortForecast"),
            "temperature": fmt_temp(wx.get("temperature")),
            "windSpeed": fmt_wind(wx.get("windSpeed")),
            "precipitation": fmt_precip(wx.get("precipitation")),
            "weather_boost": wx.get("weather_boost"),
            "logo": logo_url(g["home"]),
        })

    return render_template("weather.html", rows=rows, weeks=weeks_all, week=week_sel)

# ===== Transactions (unchanged logic, just rendering) =====
@views_bp.route("/transactions")
def transactions():
    items = []

    try:
        from utils.transactions import get_transactions
        df = get_transactions()
        if df is not None:
            items = df.to_dict(orient="records")
    except Exception:
        pass

    if not items:
        data_dir = os.getenv("DATA_DIR", "DATA")
        csv_path = os.path.join(data_dir, "transactions.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                items = df.to_dict(orient="records")
            except Exception:
                items = []

    decorated = []
    for row in items:
        r = dict(row)
        team_like = (
            r.get("team") or r.get("Team") or r.get("home") or r.get("Home")
            or r.get("to_team") or r.get("from_team") or r.get("Team Name")
        )
        r["_logo"] = team_logo_url(team_like)
        r["_team_label"] = team_like
        decorated.append(r)

    return render_template("transactions.html", items=decorated)

# Trigger a simulation (Week X)
@views_bp.route('/simulate', methods=['POST'])
@login_required
def simulate():
    week = request.form.get('week', type=int)
    if not week or week < 1 or week > 18:
        flash("Please pick a valid week (1–18).", "error")
        return redirect(url_for('views.home'))

    try:
        app_root = Path(current_app.root_path).parent  # project root
        sim_py = app_root / "sim_engine.py"

        # Prefer in-process function if available
        try:
            from sim_engine import run_week
            run_week(week=week)
            flash(f"Week {week} simulation completed.", "success")
        except Exception:
            # Fallback: background process so UI returns immediately
            subprocess.Popen(
                [sys.executable, str(sim_py), "--week", str(week)],
                cwd=str(app_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                shell=False
            )
            flash(f"Week {week} simulation started in background.", "success")

    except Exception as e:
        current_app.logger.exception("Sim trigger failed")
        flash(f"Failed to start simulation: {e}", "error")

    return redirect(url_for('views.week_view', week=week))
