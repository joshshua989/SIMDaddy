#!/usr/bin/env python3
"""
Scrape FantasyPros NFL injury news and save monthly CSVs with NO row cap.

- Crawls ?page=1..N (you choose how deep with --max-pages)
- Parses fields: headline, date, description, fantasy_impact, player_name
- Parses/normalizes dates, groups by YYYY-MM
- Writes/merges to DATA/injuries/injuries_YYYY-MM.csv
- Dedupes per month by (player_name, date, headline), keeping newest first
- Default years: 2024 and 2025. You can pass others via --years.

Examples:
  python scripts/scrape_fantasypros_injuries.py
  python scripts/scrape_fantasypros_injuries.py --years 2024,2025,2023 --max-pages 80
  python scripts/scrape_fantasypros_injuries.py --max-pages 60  # go deeper to reach older months
"""

import os
import re
import time
import argparse
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd
from dateutil import parser as dateparser
from datetime import datetime, timezone

BASE_URL = "https://www.fantasypros.com/nfl/injury-news.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
REQUEST_DELAY_SEC = 1.2  # polite crawl delay
OUTDIR = os.path.join("DATA", "injuries")


def fetch_page(page: int) -> Optional[str]:
    params = {} if page == 1 else {"page": page}
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    print(f"Fetching page {page}: {url}")
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
    if resp.status_code != 200:
        print(f"  ! HTTP {resp.status_code}")
        return None
    return resp.text


def clean_ordinals(s: str) -> str:
    # "Aug 10th" -> "Aug 10"
    return re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s)


def parse_date(text: str) -> Optional[datetime]:
    if not text:
        return None
    try:
        # ex: "Sun, Aug 10th 6:32pm EDT"
        t = clean_ordinals(text)
        dt = dateparser.parse(t, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def extract_items(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("div", class_="player-news-item")
    items = []
    for article in articles:
        try:
            header = article.find("div", class_="player-news-header")
            headline_tag = header.find("a") if header else None
            headline = headline_tag.text.strip() if headline_tag else None

            date_tag = header.find("p") if header else None
            date_txt = date_tag.text.strip().split("By")[0].strip() if date_tag else None

            ten_columns_div = article.find("div", class_="ten columns")
            p_tags = ten_columns_div.find_all("p", recursive=False) if ten_columns_div else []

            description = None
            fantasy_impact = None
            found_description = False
            for p in p_tags:
                text = p.get_text(strip=True)
                if not found_description and "Fantasy Impact" not in text and "By" not in text:
                    description = text
                    found_description = True
                elif "Fantasy Impact" in text:
                    fantasy_impact = text.replace("Fantasy Impact:", "").strip()
                    break

            # Simple player_name heuristic (matches your app)
            player_name = None
            if isinstance(headline, str) and headline.strip():
                player_name = " ".join(headline.split()[:2])

            items.append({
                "headline": headline,
                "date": date_txt,
                "description": description,
                "fantasy_impact": fantasy_impact,
                "player_name": player_name,
            })
        except Exception as e:
            print(f"  ! Error parsing article: {e}")
    return items


def scrape(max_pages: int) -> pd.DataFrame:
    rows: List[Dict] = []
    for page in range(1, max_pages + 1):
        html = fetch_page(page)
        if not html:
            break
        page_items = extract_items(html)
        if not page_items:
            # likely end of listings
            break
        rows.extend(page_items)
        time.sleep(REQUEST_DELAY_SEC)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["_date_parsed"] = df["date"].apply(parse_date)
        df = df.sort_values("_date_parsed", ascending=False, na_position="last")
    print(f"Scraped total rows: {len(df)}")
    return df


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["player_name", "headline", "date", "description", "fantasy_impact"]
    for c in cols:
        if c not in df.columns:
            df[c] = None
        df[c] = df[c].astype(str).replace({"None": ""})
    if "_date_parsed" not in df.columns:
        df["_date_parsed"] = df["date"].apply(parse_date)
    df = df.sort_values("_date_parsed", ascending=False, na_position="last")
    ordered = ["date", "player_name", "headline", "description", "fantasy_impact"]
    for c in ordered:
        if c not in df.columns:
            df[c] = None
    return df[ordered + [c for c in df.columns if c not in ordered]]


def dedupe_keep_newest(df: pd.DataFrame) -> pd.DataFrame:
    # Deduplicate by (player_name, date, headline), case-insensitive
    df["_key"] = df.apply(
        lambda r: f"{str(r.get('player_name') or '').strip().lower()}|"
                  f"{str(r.get('date') or '').strip().lower()}|"
                  f"{str(r.get('headline') or '').strip().lower()}",
        axis=1
    )
    df = df.drop_duplicates(subset=["_key"], keep="first").drop(columns=["_key"], errors="ignore")
    return df


def merge_save_month(df_month: pd.DataFrame, ym: str, outdir: str):
    ensure_dir(outdir)
    out_path = os.path.join(outdir, f"injuries_{ym}.csv")
    if os.path.exists(out_path):
        try:
            existing = pd.read_csv(out_path)
        except Exception:
            existing = pd.DataFrame()
    else:
        existing = pd.DataFrame()

    merged = pd.concat([existing, df_month], ignore_index=True)
    if "_date_parsed" not in merged.columns:
        merged["_date_parsed"] = merged["date"].apply(parse_date)
    merged = merged.sort_values("_date_parsed", ascending=False, na_position="last")
    merged = dedupe_keep_newest(merged)
    merged = merged.drop(columns=["_date_parsed"], errors="ignore")
    merged.to_csv(out_path, index=False)
    print(f"  -> wrote {len(merged)} rows to {out_path}")


def main():
    ap = argparse.ArgumentParser(description="Scrape FantasyPros injury news and save monthly CSVs (no cap).")
    ap.add_argument("--years", type=str, default="2024,2025",
                    help="Comma-separated years to keep (default: 2024,2025)")
    ap.add_argument("--max-pages", type=int, default=60,
                    help="How many pages to crawl (default: 60; increase to reach older months)")
    ap.add_argument("--outdir", type=str, default=OUTDIR,
                    help="Output dir for CSVs (default: DATA/injuries)")
    args = ap.parse_args()

    years = []
    try:
        years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    except Exception:
        print("--years must be comma-separated integers, e.g. 2024,2025")
        return
    years_set = set(years)

    df = scrape(max_pages=args.max_pages)
    if df.empty:
        print("No rows scraped.")
        return

    # filter to the chosen years
    df = df[df["_date_parsed"].notna()]
    df = df[df["_date_parsed"].dt.year.isin(years_set)].copy()
    if df.empty:
        print(f"No rows in selected years: {sorted(years_set)}")
        return

    df = normalize_df(df)
    df["_ym"] = df["_date_parsed"].dt.strftime("%Y-%m")

    # Save each month (YYYY-MM) into its own CSV
    for ym, chunk in df.groupby("_ym", sort=False):
        year_int = int(ym.split("-")[0])
        if year_int not in years_set:
            continue
        print(f"Month {ym}: {len(chunk)} rows before merge")
        merge_save_month(chunk.drop(columns=["_ym"], errors="ignore"), ym, args.outdir)


if __name__ == "__main__":
    # Please check FantasyPros' robots.txt/ToS before heavy scraping.
    main()
