# views/routes.py

from flask import Blueprint, render_template, session, redirect, url_for, request, flash, current_app, abort
from flask_login import login_required, current_user
import os, sys, subprocess, time
from pathlib import Path
import pandas as pd
from datetime import datetime
from sqlalchemy import or_, func, and_
import hashlib, math, re

from utils.injury_reports import get_injury_reports
from config import NFL_SCHEDULE_2025_FILE, STADIUM_ENV_FILE
from utils.team_logo import logo_url_for_code, team_logo_url
from utils.player_team import team_for_player

import csv
from werkzeug.utils import secure_filename
from config import ALLOWED_IMAGE_EXTENSIONS, BASE_DIR

# Wallet/entitlement helpers
from services.wallet import (
    get_or_create_wallet, earn_coins, spend_coins, add_rep,
    grant_entitlement, has_entitlement
)
from models.wallet import Wallet, CoinTxn, RepEvent, Entitlement

# NEW: product pricing config
from config import get_week_product, get_season_product

# NEW: DK model
from models.dk import DKEntry
from extensions import db

views_bp = Blueprint('views', __name__)

# Make 'os' available in all templates (for the avatar preset loop)
@views_bp.app_context_processor
def inject_os():
    return dict(os=os)

# Where weekly CSV outputs land for the dashboard (adjust if yours differs)
DATA_DIR = 'DATA/sim_results'

TEAM_COLORS = {
    "CIN": "#FB4F14", "DET": "#0076B6", "PHI": "#004C54", "DAL": "#041E42", "BUF": "#00338D",
    # ...add all as needed
}

# ----- Common helpers -----
def matchup_bg_color(adj_pts):
    try:
        adj_pts = float(adj_pts)
        if adj_pts >= 18:
            return "#24d35d"
        elif adj_pts >= 15:
            return "#ffdf5b"
        else:
            return "#ef6161"
    except:
        return "#bbb"

# =========================
#          ROUTES
# =========================

@views_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@views_bp.route("/terms")
def terms():
    return render_template("terms.html")

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
    Load injury reports, attach logo URLs via player->team or text inference,
    and paginate results at 10 per page while keeping a stable total_count.
    Use ?refresh=1 to bypass the 5-min scrape cache once.
    """
    PAGE_SIZE = 10
    page = request.args.get("page", 1, type=int) or 1
    max_pages = request.args.get("pages", default=8, type=int)
    refresh = request.args.get("refresh", type=int) == 1  # <— NEW

    # Pull the full dataset so total_count is stable
    df = get_injury_reports(
        max_pages=max_pages,
        target_items=None,   # do not early-stop; get full set
        concurrency=3,
        use_cache=not refresh,   # <— NEW: bypass cache when refresh=1
        verbose=False,
    )

    if df is None or df.empty:
        flash("No injury data available right now.", "warning")
        return render_template(
            "injuries.html",
            injuries=[],
            total_count=0,
            page=1,
            total_pages=1,
            page_size=PAGE_SIZE,
            showing_start=0,
            showing_end=0,
        )

    # Convert to records
    items = df.to_dict(orient="records")

    # Attach logo URLs — prefer player->team via roster, then text inference
    for it in items:
        player = (it.get("player_name") or it.get("player") or "").strip()
        logo = None

        # 1) Try roster map
        if player:
            code = team_for_player(player)
            if code:
                logo = logo_url_for_code(code)

        # 2) Fallback: infer from headline + description
        if not logo:
            text = " ".join(filter(None, [it.get("headline", ""), it.get("description", "")]))
            logo = team_logo_url(text)

        it["logo_url"] = logo

    total_count = len(items)
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    injuries_page = items[start:end]

    return render_template(
        "injuries.html",
        injuries=injuries_page,
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

# -------------------------------
# Update Avatar (upload or preset)
# -------------------------------
@views_bp.route('/account/avatar', methods=['POST'])
@login_required
def update_avatar():
    from werkzeug.utils import secure_filename
    from config import AVATAR_UPLOAD_DIR, ALLOWED_AVATAR_EXTS, MAX_AVATAR_SIZE_MB
    from pathlib import Path
    import os

    # Ensure upload directory exists
    try:
        os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)
    except Exception:
        pass

    preset = request.form.get('preset') or ''
    file = request.files.get('file')
    new_url = None

    # Remove any previous user_<id>.* avatar files
    try:
        up_base = Path(current_app.root_path).parent / AVATAR_UPLOAD_DIR
        up_base.mkdir(parents=True, exist_ok=True)
        for p in up_base.glob(f'user_{current_user.id}.*'):
            try: p.unlink()
            except Exception: pass
    except Exception:
        pass

    # 1) Preset
    if preset:
        preset = preset.strip().replace('..','')
        preset_path = Path(current_app.root_path).parent / 'static' / 'images' / 'avatars' / preset
        if preset_path.exists():
            new_url = url_for('static', filename=f'images/avatars/{preset}', _external=False)
        else:
            flash('Selected preset not found.', 'error')
            return redirect(url_for('views.account'))

    # 2) Upload
    elif file and file.filename:
        fname = secure_filename(file.filename)
        ext = os.path.splitext(fname)[1].lower()
        if ext not in ALLOWED_AVATAR_EXTS:
            flash('Unsupported file type.', 'error')
            return redirect(url_for('views.account'))

        # size check
        try:
            file.seek(0, os.SEEK_END); size = file.tell(); file.seek(0)
        except Exception:
            size = 0
        if size > MAX_AVATAR_SIZE_MB * 1024 * 1024:
            flash(f'File too large (>{MAX_AVATAR_SIZE_MB}MB).', 'error')
            return redirect(url_for('views.account'))

        out_base = Path(current_app.root_path).parent / AVATAR_UPLOAD_DIR
        out_base.mkdir(parents=True, exist_ok=True)

        try:
            if ext != '.svg':
                try:
                    from PIL import Image
                    im = Image.open(file)
                    try: im.seek(0)
                    except Exception: pass
                    im = im.convert('RGB')
                    im.thumbnail((256, 256))
                    out_name = f'user_{current_user.id}.webp'
                    out_path = out_base / out_name
                    im.save(out_path, 'WEBP', quality=80, method=6)
                    new_url = url_for('static', filename=f'uploads/avatars/{out_name}', _external=False)
                except Exception:
                    out_name = f'user_{current_user.id}{ext}'
                    out_path = out_base / out_name
                    file.stream.seek(0)
                    file.save(out_path)
                    new_url = url_for('static', filename=f'uploads/avatars/{out_name}', _external=False)
            else:
                out_name = f'user_{current_user.id}.svg'
                out_path = out_base / out_name
                file.save(out_path)
                new_url = url_for('static', filename=f'uploads/avatars/{out_name}', _external=False)
        except Exception as e:
            current_app.logger.exception("Failed to save avatar: %s", e)
            flash('Failed to save avatar.', 'error')
            return redirect(url_for('views.account'))
    else:
        flash('No avatar selected.', 'error')
        return redirect(url_for('views.account'))

    try:
        current_user.avatar_url = new_url
        db.session.commit()
        flash('Profile picture updated.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Failed to update avatar on user: %s", e)
        flash('Failed to update profile picture.', 'error')

    return redirect(url_for('views.account'))

# =======================
# DraftKings CSV Import
# =======================

def _col(df, *cands):
    """Find a column in df by candidate names (case/space-insensitive)."""
    key = lambda s: s.lower().strip().replace(" ", "").replace("_","")
    norm = {key(c): c for c in df.columns}
    for cand in cands:
        if key(cand) in norm:
            return norm[key(cand)]
    return None

def _to_float(x):
    try:
        s = str(x or "").strip()
        if s in ("", "—", "-", "–", "None", "nan", "NaN"):
            return 0.0
        s = s.replace("$","").replace(",","")
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        return float(s)
    except Exception:
        return 0.0

def _to_dt(x):
    if x is None:
        return None
    s = str(x).strip()
    # common DK formats + fallback date-only
    fmts = (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M",
        "%m/%d/%Y", "%Y-%m-%d"
    )
    from datetime import datetime
    for fmt in fmts:
        try:
            return datetime.strptime(s.split(" ")[0], fmt)
        except Exception:
            pass
    return None

_ws_re = re.compile(r"\s+")
def _norm_name(s):
    s = (s or "").strip().lower()
    return _ws_re.sub(" ", s)

def _norm_date_key(dt):
    try:
        return dt.date().isoformat()
    except Exception:
        return ""

def _synth_entry_id(name, when, buy_in, fpts):
    import hashlib
    n = _norm_name(name)
    d = _norm_date_key(when)
    b = round(float(buy_in or 0.0), 2)
    p = round(float(fpts or 0.0), 2)
    sig = f"{n}|{d}|{b:.2f}|{p:.2f}"
    return hashlib.sha1(sig.encode("utf-8")).hexdigest()[:16]

def _soft_find_existing(user_id, name, when, buy_in, fpts):
    """Match an older row even if entry_id differs (tolerant match)."""
    from sqlalchemy import and_, func
    nkey = _norm_name(name)
    dkey = _norm_date_key(when)

    qset = DKEntry.query.filter(DKEntry.user_id == user_id)
    if dkey:
        qset = qset.filter(func.date(DKEntry.contest_date) == dkey)
    else:
        qset = qset.filter(DKEntry.contest_date.is_(None))

    b = round(float(buy_in or 0.0), 2)
    p = round(float(fpts or 0.0), 2)
    qset = qset.filter(
        and_((DKEntry.buy_in - b) <= 0.01, (DKEntry.buy_in - b) >= -0.01),
        and_((DKEntry.fpts   - p) <= 0.01, (DKEntry.fpts   - p) >= -0.01),
    )
    for cand in qset.limit(50).all():
        if _norm_name(cand.contest_name) == nkey:
            return cand
    return None

@views_bp.route("/account/dk/import", methods=["GET", "POST"])
@login_required
def dk_import():
    from extensions import db
    from models.dk import DKEntry
    from sqlalchemy import or_, func
    import pandas as pd
    import io
    from pathlib import Path

    # --- table query params ---
    q = (request.args.get("q") or "").strip()
    page = request.args.get("page", type=int) or 1
    PAGE_SIZE = 10

    # ----- GET: render searchable table -----
    if request.method == "GET":
        base = DKEntry.query.filter_by(user_id=current_user.id)
        qset = base
        if q:
            like = f"%{q}%"
            qset = qset.filter(or_(DKEntry.contest_name.ilike(like),
                                   DKEntry.entry_id.ilike(like)))
        total = qset.count()
        total_pages = max(1, math.ceil(total / PAGE_SIZE))
        page = max(1, min(page, total_pages))
        rows = (qset.order_by(DKEntry.contest_date.desc().nullslast(), DKEntry.id.desc())
                    .offset((page-1)*PAGE_SIZE)
                    .limit(PAGE_SIZE)
                    .all())
        agg = base.with_entities(
            func.coalesce(func.sum(DKEntry.buy_in), 0.0),
            func.coalesce(func.sum(DKEntry.payout), 0.0),
        ).first()
        lifetime = {"count": base.count(),
                    "buyins": float(agg[0] or 0.0),
                    "payouts": float(agg[1] or 0.0)}
        showing_start = 0 if total == 0 else ((page - 1) * PAGE_SIZE + 1)
        showing_end = min(page * PAGE_SIZE, total)
        return render_template(
            "dk_import.html",
            preview=None, import_stats=None, summary=None, lifetime=lifetime,
            entries=rows, q=q, page=page, total_pages=total_pages, total=total, page_size=PAGE_SIZE,
            showing_start=showing_start, showing_end=showing_end
        )

    # ----- POST: upload + import -----
    # (A) Optionally wipe existing rows before import
    wipe_first = request.form.get("wipe_first") == "1"
    if wipe_first:
        DKEntry.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
        db.session.commit()

    # (B) Validate file
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".csv"):
        flash("Please upload a .csv file.", "warning")
        return redirect(url_for("views.dk_import", q=q, page=page))

    # Save raw copy: DATA/dk_imports/<user_id>/<timestamp>_<filename>
    try:
        base_data_dir = Path(current_app.config.get("SIMDADDY_DATA_DIR") or "DATA")
        user_dir = base_data_dir / "dk_imports" / str(current_user.id)
        user_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", f.filename or "dk.csv")
        raw_path = user_dir / f"{ts}_{safe_name}"
        f.seek(0)
        raw_bytes = f.read()
        raw_path.write_bytes(raw_bytes)
        f = io.BytesIO(raw_bytes)  # reset for pandas
    except Exception:
        f.seek(0)

    # Load CSV robustly
    try:
        df = pd.read_csv(f)
    except Exception:
        f.seek(0)
        df = pd.read_csv(f, encoding="utf-8", engine="python")

    # === HEADER MAPPING (based on your DK headers) ===
    # "Sport","Game_Type","Entry_Key","Entry","Contest_Key","Contest_Date_EST",
    # "Place","Points","Winnings_Non_Ticket","Winnings_Ticket",
    # "Contest_Entries","Entry_Fee","Prize_Pool","Places_Paid"
    c_entry_id   = _col(df, "Entry_Key", "Entry ID", "EntryID")
    c_contest_id = _col(df, "Contest_Key", "Contest ID")
    c_contest    = _col(df, "Entry", "Contest Name", "Contest")  # show this as name
    c_date       = _col(df, "Contest_Date_EST", "Contest Date", "Date", "Start Time", "Start Time ET")
    c_points     = _col(df, "Points", "FPTS", "Fantasy Points")
    c_fee        = _col(df, "Entry_Fee", "Entry Fee", "Buy-in", "BuyIn")
    c_win_nt     = _col(df, "Winnings_Non_Ticket", "Winnings", "Payout")
    c_win_t      = _col(df, "Winnings_Ticket")  # tickets component

    # Preview (top 10)
    preview_cols = [c for c in [c_contest, c_entry_id, c_fee, c_points, c_date, c_win_nt, c_win_t] if c]
    preview = df[preview_cols].head(10) if preview_cols else None
    if preview is not None and getattr(preview, "empty", False):
        preview = None

    import_total = len(df)
    imported = skipped = updated = 0
    buyins = payouts = 0.0

    for _, r in df.iterrows():
        name = str(r.get(c_contest) or "").strip() if c_contest else ""
        when = _to_dt(r.get(c_date)) if c_date else None
        buy_in = round(_to_float(r.get(c_fee)) if c_fee else 0.0, 2)
        fpts = round(_to_float(r.get(c_points)) if c_points else 0.0, 2)

        # payout = non-ticket + ticket (default 0)
        p_nt = _to_float(r.get(c_win_nt)) if c_win_nt else 0.0
        p_tk = _to_float(r.get(c_win_t)) if c_win_t else 0.0
        payout_val = round(max(p_nt + p_tk, 0.0), 2)

        entry_id = (str(r.get(c_entry_id)).strip() if c_entry_id else "") or ""
        if not entry_id:
            entry_id = _synth_entry_id(name, when, buy_in, fpts)

        # exact match by entry_id
        exists = DKEntry.query.filter_by(user_id=current_user.id, entry_id=entry_id).first()
        if not exists:
            # tolerant match
            exists = _soft_find_existing(current_user.id, name, when, buy_in, fpts)

        if exists:
            changed = False
            if (payout_val or 0.0) > (exists.payout or 0.0):
                exists.payout = payout_val; changed = True
            if (exists.buy_in or 0.0) == 0.0 and buy_in > 0:
                exists.buy_in = buy_in; changed = True
            if (not exists.contest_name) and name:
                exists.contest_name = name; changed = True
            if (exists.contest_date is None) and when is not None:
                exists.contest_date = when; changed = True
            if (exists.fpts or 0.0) == 0.0 and fpts > 0.0:
                exists.fpts = fpts; changed = True
            if changed: updated += 1
            else: skipped += 1
            continue

        rec = DKEntry(
            user_id=current_user.id,
            contest_id=(str(r.get(c_contest_id)).strip() if c_contest_id else None),
            entry_id=entry_id,
            contest_name=name or None,
            buy_in=buy_in,
            payout=payout_val,
            fpts=fpts,
            contest_date=when
        )
        db.session.add(rec)
        imported += 1
        buyins += buy_in
        payouts += payout_val

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("DK import failed: %s", e)
        flash("Import failed. Please check your file and try again.", "error")
        return redirect(url_for("views.dk_import", q=q, page=page))

    # lifetime aggregates (post-import)
    base = DKEntry.query.filter_by(user_id=current_user.id)
    agg = base.with_entities(
        func.coalesce(func.sum(DKEntry.buy_in), 0.0),
        func.coalesce(func.sum(DKEntry.payout), 0.0),
    ).first()
    lifetime = {"count": base.count(),
                "buyins": float(agg[0] or 0.0),
                "payouts": float(agg[1] or 0.0)}

    # refresh table view
    qset = base
    if q:
        like = f"%{q}%"
        qset = qset.filter(or_(DKEntry.contest_name.ilike(like), DKEntry.entry_id.ilike(like)))
    total = qset.count()
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    rows = (qset.order_by(DKEntry.contest_date.desc().nullslast(), DKEntry.id.desc())
                .offset((page-1)*PAGE_SIZE).limit(PAGE_SIZE).all())

    import_stats = type("S", (), {"total": import_total})
    summary = {"imported": imported, "updated": updated, "skipped": skipped,
               "buyins": buyins, "payouts": payouts}
    flash(f"{'Replaced everything and ' if wipe_first else ''}Imported {imported} · Updated {updated} · Skipped {skipped}.", "success")

    showing_start = 0 if total == 0 else ((page - 1) * PAGE_SIZE + 1)
    showing_end = min(page * PAGE_SIZE, total)

    return render_template(
        "dk_import.html",
        preview=preview, import_stats=import_stats, summary=summary, lifetime=lifetime,
        entries=rows, q=q, page=page, total_pages=total_pages, total=total, page_size=PAGE_SIZE,
        showing_start=showing_start, showing_end=showing_end
    )

# Allowed for DK CSVs (legacy route kept if your UI still posts here)
ALLOWED_DK_EXTS = {'.csv'}

@views_bp.route("/account/import_dk_csv", methods=["POST"])
@login_required
def import_dk_csv():
    # redirect legacy form posts to the main importer
    return redirect(url_for("views.dk_import"))

@views_bp.route("/account/dk/summary")
@login_required
def dk_summary():
    # Aggregate totals for KPI cards
    q = DKEntry.query.filter_by(user_id=current_user.id)
    count = q.count()
    agg = q.with_entities(
        db.func.coalesce(db.func.sum(DKEntry.buy_in), 0.0),
        db.func.coalesce(db.func.sum(DKEntry.payout), 0.0),
    ).first()
    buyins = float(agg[0] or 0.0)
    payouts = float(agg[1] or 0.0)

    # Build daily time series by contest_date (skip rows with no date)
    rows = (q
            .with_entities(DKEntry.contest_date, DKEntry.buy_in, DKEntry.payout)
            .all())

    from collections import defaultdict
    by_day_buyins = defaultdict(float)
    by_day_payouts = defaultdict(float)
    for d, fee, pay in rows:
        if not d:
            continue
        day = d.date().isoformat()
        by_day_buyins[day] += float(fee or 0.0)
        by_day_payouts[day] += float(pay or 0.0)

    labels = sorted(set(by_day_buyins.keys()) | set(by_day_payouts.keys()))
    series_buyins = [round(by_day_buyins.get(day, 0.0), 2) for day in labels]
    series_payouts = [round(by_day_payouts.get(day, 0.0), 2) for day in labels]

    summary = {"count": count, "buyins": buyins, "payouts": payouts}
    series = {"labels": labels, "buyins": series_buyins, "payouts": series_payouts}
    return render_template("dk_summary.html", summary=summary, series=series)

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
    from utils.team_logo import team_logo_url  # global resolver (local /static first, ESPN fallback)

    data_path = os.getenv("DATA_DIR", "DATA")

    # ---- Load schedule (unchanged) ----
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

    # Dedup by home team to avoid duplicates
    seen_home = set()
    games_dedup = []
    for g in games:
        h = g["home"].lower()
        if h and h not in seen_home:
            seen_home.add(h)
            games_dedup.append(g)

    # ---- Load recorded weather log (unchanged) ----
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

    # ---- Load stadium environment profile (unchanged) ----
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

    # ---- Small formatters (unchanged) ----
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

    # ---- Build rows (logo via global helper) ----
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
            "logo": team_logo_url(g["home"]),  # <— global logo resolver
        })

    return render_template("weather.html", rows=rows, weeks=weeks_all, week=week_sel)

# ===== Transactions (unchanged logic, just rendering) =====
@views_bp.route("/transactions")
def transactions():
    from utils.team_logo import team_logo_url  # global resolver (local /static first, ESPN fallback)

    items = []

    # Primary source via utils.transactions (if present)
    try:
        from utils.transactions import get_transactions
        df = get_transactions()
        if df is not None:
            items = df.to_dict(orient="records")
    except Exception:
        pass

    # Fallback CSV if utils.transactions isn't available or returns nothing
    if not items:
        data_dir = os.getenv("DATA_DIR", "DATA")
        csv_path = os.path.join(data_dir, "transactions.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                items = df.to_dict(orient="records")
            except Exception:
                items = []

    # Decorate with a logo inferred from any team-like field (global helper handles it)
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

@views_bp.route("/me/dk/reset", methods=["POST"])
@login_required
def dk_reset_self():
    """Delete the current user's DK entries and their uploaded raw files."""
    from extensions import db
    from models.dk import DKEntry
    import shutil

    uid = current_user.id
    # delete DB rows (chunked for SQLite)
    DBATCH = 500
    q = DKEntry.query.filter_by(user_id=uid)
    while True:
        rows = q.limit(DBATCH).all()
        if not rows:
            break
        for r in rows:
            db.session.delete(r)
        db.session.commit()

    # delete files
    base_data_dir = Path(current_app.config.get("SIMDADDY_DATA_DIR") or "DATA")
    user_dir = base_data_dir / "dk_imports" / str(uid)
    if user_dir.exists():
        shutil.rmtree(user_dir, ignore_errors=True)

    flash("Your DraftKings imports were reset.", "success")
    return redirect(url_for("views.dk_import"))

@views_bp.route("/admin/dk/reset/<int:user_id>", methods=["POST"])
@login_required
def dk_reset_admin(user_id):
    """Admin-only reset for another user's DK imports."""
    if not getattr(current_user, "is_admin", False):
        abort(403)

    from extensions import db
    from models.dk import DKEntry
    import shutil

    # delete DB rows
    DKEntry.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.commit()

    # delete files
    base_data_dir = Path(current_app.config.get("SIMDADDY_DATA_DIR") or "DATA")
    user_dir = base_data_dir / "dk_imports" / str(user_id)
    if user_dir.exists():
        shutil.rmtree(user_dir, ignore_errors=True)

    flash(f"DraftKings imports reset for user {user_id}.", "success")
    return redirect(url_for("views.dk_import"))
