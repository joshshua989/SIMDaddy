# utils/team_lookup.py
"""
Infer an NFL team code (e.g., 'NYJ') from free text like headlines/descriptions.

Usage:
    from utils.team_lookup import infer_team_code
    code = infer_team_code("Jets activate Jermaine Johnson from PUP list")
    # -> 'NYJ'
"""
from __future__ import annotations
import re
from typing import Optional

# Canonical code -> list of synonyms/aliases to search for (lowercase)
TEAM_SYNONYMS = {
    "ARI": ["arizona cardinals", "cardinals", "ari"],
    "ATL": ["atlanta falcons", "falcons", "atl"],
    "BAL": ["baltimore ravens", "ravens", "bal"],
    "BUF": ["buffalo bills", "bills", "buf"],
    "CAR": ["carolina panthers", "panthers", "car"],
    "CHI": ["chicago bears", "bears", "chi"],
    "CIN": ["cincinnati bengals", "bengals", "cin"],
    "CLE": ["cleveland browns", "browns", "cle"],
    "DAL": ["dallas cowboys", "cowboys", "dal"],
    "DEN": ["denver broncos", "broncos", "den"],
    "DET": ["detroit lions", "lions", "det"],
    "GB":  ["green bay packers", "packers", "gb", "gnb"],  # include legacy 'GNB'
    "HOU": ["houston texans", "texans", "hou"],
    "IND": ["indianapolis colts", "colts", "ind"],
    "JAX": ["jacksonville jaguars", "jaguars", "jags", "jax"],
    "KC":  ["kansas city chiefs", "chiefs", "kc", "kcc"],
    "LV":  ["las vegas raiders", "raiders", "lv", "oakland raiders", "oak"],
    "LAC": ["los angeles chargers", "chargers", "lac", "san diego chargers", "sd"],
    "LAR": ["los angeles rams", "rams", "lar", "st louis rams", "st. louis rams", "st louis"],
    "MIA": ["miami dolphins", "dolphins", "mia"],
    "MIN": ["minnesota vikings", "vikings", "min"],
    "NE":  ["new england patriots", "patriots", "pats", "ne", "nwe"],
    "NO":  ["new orleans saints", "saints", "no", "nor"],
    "NYG": ["new york giants", "giants", "nyg"],
    "NYJ": ["new york jets", "jets", "nyj", "gang green"],
    "PHI": ["philadelphia eagles", "eagles", "phi"],
    "PIT": ["pittsburgh steelers", "steelers", "pit"],
    "SEA": ["seattle seahawks", "seahawks", "sea"],
    "SF":  ["san francisco 49ers", "49ers", "niners", "sf", "sfo", "san francisco"],
    "TB":  ["tampa bay buccaneers", "buccaneers", "bucs", "tb", "tbb"],
    "TEN": ["tennessee titans", "titans", "ten"],
    "WAS": ["washington commanders", "commanders", "was", "washington"],
}

# Compile regexes once (longer phrases first so "los angeles chargers" wins over "chargers")
_PATTERNS: list[tuple[str, re.Pattern]] = []
for code, synonyms in TEAM_SYNONYMS.items():
    for syn in sorted(synonyms, key=len, reverse=True):
        # Word boundaries; allow flexible whitespace
        pattern = r"\b" + re.sub(r"\s+", r"\\s+", re.escape(syn)) + r"\b"
        _PATTERNS.append((code, re.compile(pattern, re.IGNORECASE)))


def infer_team_code(text: Optional[str]) -> Optional[str]:
    """
    Return a team code like 'NYJ' if we can infer one from text; else None.
    """
    if not text or not isinstance(text, str):
        return None
    for code, rx in _PATTERNS:
        if rx.search(text):
            return code
    return None
