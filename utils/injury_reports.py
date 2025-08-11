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

    return {"headline": headline, "date": date, "description": description, "fantasy_impact": fantasy_impact}

def _player_from_headline(headline: Optional[str]) -> Optional[str]:
    if not isinstance(headline, str): return None
    base = re.split(r"\s*\(|\s+-\s+", headline, maxsplit=1)[0].strip()
    toks = base.split()
    return " ".join(toks[:3]) if toks else None  # allow "II"

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
            d["player_name"] = _player_from_headline(d.get("headline"))
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
    cache_key = ("injuries", max_pages, target_items)
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
