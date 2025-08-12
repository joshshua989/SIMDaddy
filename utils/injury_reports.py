# utils/injury_reports.py

from __future__ import annotations
import re, time, concurrent.futures as cf
from typing import Optional, List, Dict, Tuple
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE_URL = "https://www.fantasypros.com/nfl/injury-news.php"
HEADERS  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# tiny in-process cache (5 minutes)
_CACHE: dict = {}
_CACHE_TTL = 300  # seconds
_CACHE_VERSION = 2  # bump this when changing parsing so stale data is ignored

# =========================
#   Name extraction rules
# =========================

# Allow:
# - Normal capitalized words: Josh, Watson
# - Mixed case like MarShawn, JuJu
# - Mc/Mac names with internal capital: McKinney, MacJones
# - Initials (A.J., DJ, D.K.)
_NAME_TOKEN = r"(?:[A-Z][a-z]+[a-zA-Z]*|[A-Z][a-z]*[A-Z][a-z]+|Mc[A-Z][a-z]+|Mac[A-Z][a-z]+|(?:[A-Z]\.?){1,3})"

# Optional suffixes like Jr., Sr., II, III, IV
_SUFFIX = r"(?:\s+(?:Jr\.|Sr\.|II|III|IV))?"

# 2 or 3 name tokens make a player name, optionally with a suffix
_NAME_SPAN = rf"(?P<name>{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{1,2}}{_SUFFIX})"

# Position-based capture like "Packers WR Christian Watson ..."
_POS_RX = re.compile(
    rf"\b(?:QB|RB|WR|TE|FB|LB|CB|DB|S|DL|DE|DT|OL)\b[\s/,-]+{_NAME_SPAN}",
    re.IGNORECASE
)

# Stop words we expect AFTER a name in headlines
_STOP_WORDS = (
    "does|do|did|is|was|were|has|have|had|will|won't|not|expected|likely|questionable|doubtful|"
    "out|limited|ruled|placed|activated|designated|return|returns|sign|signs|agrees|agreed|lands|"
    "suffers|diagnosed|undergoes|practice|practices|practicing|miss|misses|to|with|after|from|for|"
    "vs|vs\\.|versus|and|at|in|on|leaves|dealing|waived|sitting|believed|sidelined"
)

# Capture a name immediately before a stop word:
# e.g., "A.J. Brown expected ..." / "DJ Johnson not ..."
_NAME_BEFORE_STOP = re.compile(
    rf"\b{_NAME_SPAN}\b\s+(?:{_STOP_WORDS})\b",
    re.IGNORECASE
)

# Team nouns to avoid mistaking for names
_TEAM_NOUNS = {
    "49ers","niners","bears","bengals","bills","broncos","browns","buccaneers","bucs","cardinals",
    "chargers","chiefs","colts","commanders","cowboys","dolphins","eagles","falcons","giants",
    "jaguars","jags","jets","lions","packers","panthers","patriots","pats","raiders","rams",
    "ravens","saints","seahawks","steelers","texans","titans","vikings"
}

def _strip_suffixes(s: str) -> str:
    # Remove anything after " - " (source) or first "("
    return re.split(r"\s*\(|\s+-\s+", s, maxsplit=1)[0].strip()

def _is_plausible_name(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if t.lower() in _TEAM_NOUNS:
        return False
    # 2–3 tokens required
    tokens = t.split()
    if len(tokens) < 2 or len(tokens) > 4:
        return False
    return all(re.fullmatch(_NAME_TOKEN, tok) for tok in tokens)

def _scan_start_until_stop(text: str) -> Optional[str]:
    if not text:
        return None
    parts: List[str] = []
    stop_set = {w.replace("\\.", "") for w in _STOP_WORDS.split("|")}
    for raw in text.split():
        tok = raw.strip(".,:;!?\"'()").replace("’", "'")
        if tok.lower() in stop_set:
            break
        if re.fullmatch(_NAME_TOKEN, tok):
            parts.append(tok)
            if len(parts) >= 3:
                break
        else:
            break
    name = " ".join(parts).strip()
    return name if _is_plausible_name(name) else None

def _first_match(regex: re.Pattern, text: str) -> Optional[str]:
    m = regex.search(text)
    return m.group("name").strip() if m else None

def _extract_player_name(headline: Optional[str], description: Optional[str]) -> Optional[str]:
    """
    Robust player-name extractor using headline, with description fallback.
    Order:
      1) POS-based (WR/RB/QB/TE/etc.)
      2) Name before stop word
      3) Start-of-line scan (until stop word)
      4) Repeat 2+3 on description
    """
    head = _strip_suffixes(headline or "")
    desc = _strip_suffixes(description or "")

    # 1) POS-based
    name = _first_match(_POS_RX, head)
    if name and _is_plausible_name(name):
        return name

    # 2) Before-stop in headline
    name = _first_match(_NAME_BEFORE_STOP, head)
    if name and _is_plausible_name(name):
        return name

    # 3) Start-of-line scan in headline
    name = _scan_start_until_stop(head)
    if name and _is_plausible_name(name):
        return name

    # 4) Description fallback (for headlines like "waived by Browns", "day", etc.)
    if desc:
        name = _first_match(_NAME_BEFORE_STOP, desc)
        if name and _is_plausible_name(name):
            return name
        name = _scan_start_until_stop(desc)
        if name and _is_plausible_name(name):
            return name

    return None

# =========================
#   Scraper core
# =========================

def _page_url(p: int) -> str:
    return BASE_URL if p <= 1 else f"{BASE_URL}?page={p}"

def _parser_name() -> str:
    try:
        import lxml  # noqa: F401
        return "lxml"
    except Exception:
        return "html.parser"

def _extract_text(el) -> str:
    return el.get_text(" ", strip=True) if el else ""

def _parse_article(div) -> Dict[str, Optional[str]]:
    header = div.find("div", class_="player-news-header")
    headline_tag = header.find("a") if header else None
    headline = _extract_text(headline_tag) or None

    date_tag = header.find("p") if header else None
    date_text = _extract_text(date_tag)
    date = date_text.split(" By ")[0].strip() if date_text else None

    description = None
    fantasy_impact = None
    ten_cols = div.find("div", class_="ten columns")
    p_tags = ten_cols.find_all("p", recursive=False) if ten_cols else div.find_all("p")
    found_description = False
    for p in p_tags:
        text = _extract_text(p)
        if not text:
            continue
        if "Fantasy Impact" in text:
            fantasy_impact = text.replace("Fantasy Impact", "").replace(":", "").strip()
            continue
        if "Source:" in text or " By " in text:
            continue
        if not found_description:
            description = text
            found_description = True

    player_name = _extract_player_name(headline, description)

    return {
        "player_name": player_name,
        "headline": headline,
        "date": date,
        "description": description,
        "fantasy_impact": fantasy_impact
    }

def _fetch_page(p: int, timeout: int = 10) -> Tuple[int, List[Dict[str, Optional[str]]], bool]:
    """
    Returns (page_number, items, is_empty_or_error)
    """
    url = _page_url(p)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 404:
            return p, [], True
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, _parser_name())
        articles = soup.find_all("div", class_="player-news-item")
        if not articles:
            return p, [], True
        items = []
        for a in articles:
            d = _parse_article(a)
            if not d.get("player_name"):
                d["player_name"] = _extract_player_name(d.get("headline"), d.get("description"))
            items.append(d)
        return p, items, False
    except requests.RequestException:
        return p, [], True

def get_injury_reports(
    max_pages: Optional[int] = 8,     # upper bound; None to keep going until an empty page
    target_items: Optional[int] = None,  # early-stop when we have this many rows
    concurrency: int = 3,            # polite, small parallelism
    use_cache: bool = True,
    verbose: bool = False,
) -> pd.DataFrame:
    """
    Fast + safe scraper:
      • Walk pages until empty/404 (or until max_pages).
      • Parallel-fetch small batches for speed.
      • Early-stop once `target_items` rows collected.
      • Caches the aggregated result for 5 minutes.
    """
    cache_key = ("injuries", _CACHE_VERSION, max_pages, target_items)
    now = time.time()
    if use_cache and cache_key in _CACHE and now - _CACHE[cache_key][0] < _CACHE_TTL:
        if verbose: print("[injuries] cache hit")
        return _CACHE[cache_key][1].copy()

    rows: List[Dict[str, Optional[str]]] = []
    seen: set[Tuple[Optional[str], Optional[str]]] = set()

    page = 1
    batch = max(1, min(concurrency, 6))
    stop = False

    while not stop:
        # build next batch respecting max_pages
        upper = page + batch - 1
        if max_pages is not None:
            upper = min(upper, max_pages)
        pages = [p for p in range(page, upper + 1)]
        if not pages:
            break

        # fetch batch in parallel
        with cf.ThreadPoolExecutor(max_workers=batch) as ex:
            for p, items, empty in ex.map(_fetch_page, pages):
                if verbose: print(f"[injuries] page {p}: {len(items)} items{' (empty)' if empty else ''}")
                if empty:
                    # if the first missing page is hit, we can stop scanning higher pages
                    stop = True
                else:
                    for it in items:
                        key = (it.get("headline"), it.get("date"))
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(it)
                        if target_items is not None and len(rows) >= target_items:
                            stop = True
                            break
            # end for
        # advance to next block
        page = upper + 1
        if max_pages is not None and page > max_pages:
            break

    df = pd.DataFrame(rows, columns=["player_name","headline","date","description","fantasy_impact"])
    if use_cache:
        _CACHE[cache_key] = (now, df.copy())
    if verbose: print(f"[injuries] total rows: {len(df)}")
    return df
