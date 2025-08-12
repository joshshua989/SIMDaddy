# utils/team_logos.py
"""
Global NFL logo registry.
- Auto-discovers /static/logos/*.png or *.svg at runtime.
- Normalizes many input codes (JAX->jac, WAS->wsh, etc.).
- Exposes get_team_logo_url(code) to return the local static URL if present.
"""

from __future__ import annotations
import os
from functools import lru_cache
from typing import Optional
from flask import current_app, url_for

# Canonical ESPN 3-letter slugs (lowercase) we normalize to
CANON = [
    "ari","atl","bal","buf","car","chi","cin","cle","dal","den","det","gb","hou","ind","jac","kc",
    "lv","lac","lar","mia","min","ne","no","nyg","nyj","phi","pit","sea","sf","tb","ten","wsh"
]

# Common aliases -> canonical ESPN slug
ALIASES = {
    # case/legacy variants
    "SF": "sf", "ARI": "ari", "ATL": "atl", "BAL": "bal", "BUF": "buf", "CAR": "car",
    "CHI": "chi", "CIN": "cin", "CLE": "cle", "DAL": "dal", "DEN": "den", "DET": "det",
    "GB": "gb", "GNB": "gb", "HOU": "hou", "IND": "ind",
    "JAX": "jac", "JAC": "jac",
    "KC": "kc", "KAN": "kc",
    "LV": "lv", "OAK": "lv",
    "LAC": "lac", "SD": "lac",
    "LAR": "lar", "STL": "lar",
    "MIA": "mia", "MIN": "min", "NE": "ne", "NO": "no", "NOR": "no",
    "NYG": "nyg", "NYJ": "nyj", "PHI": "phi", "PIT": "pit", "SEA": "sea",
    "TB": "tb", "TEN": "ten",
    "WAS": "wsh", "WSH": "wsh",
    # Already canonical (accept as-is)
    **{c.upper(): c for c in CANON},
    **{c: c for c in CANON},
}

def normalize_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    c = str(code).strip()
    if not c:
        return None
    return ALIASES.get(c, ALIASES.get(c.upper(), c.lower()))

@lru_cache(maxsize=128)
def _scan_static_dir() -> dict[str, str]:
    """
    Scan /static/logos for PNG/SVG (case-insensitive file names).
    Build a map: canonical slug (lowercase) -> static URL path ("logos/XXX.png").
    """
    mapping: dict[str, str] = {}
    try:
        root = current_app.root_path  # requires app context
    except Exception:
        return mapping

    logos_fs = os.path.join(root, "static", "logos")
    if not os.path.isdir(logos_fs):
        return mapping

    for fn in os.listdir(logos_fs):
        lower = fn.lower()
        if not (lower.endswith(".png") or lower.endswith(".svg")):
            continue
        stem = lower.rsplit(".", 1)[0]  # e.g., "nyj"
        # Map uppercase filenames too (you downloaded "NYJ.png")
        # We'll try to match to canonical if possible
        canon = normalize_code(stem)
        if not canon:
            continue
        # Prefer PNG over SVG if both exist (overwrite SVG if PNG shows up later)
        rel = f"logos/{fn}"
        # If file is uppercase in FS, rel must match FS exactly
        # so use the real filename `fn` (not lowercased)
        mapping[canon] = rel
    return mapping

def get_team_logo_url(code: Optional[str]) -> Optional[str]:
    """
    Return /static path for team code if we have it locally; else None.
    """
    canon = normalize_code(code)
    if not canon:
        return None
    rel = _scan_static_dir().get(canon)
    if not rel:
        return None
    try:
        return url_for("static", filename=rel)
    except Exception:
        return None
