# utils/player_team.py
from __future__ import annotations
import os, re
from functools import lru_cache
from typing import Optional

import pandas as pd
from flask import current_app

# Normalize player names for matching
def _norm_name(name: str) -> str:
    s = str(name or "").strip().lower()
    # remove punctuation, collapse spaces
    s = re.sub(r"[.\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

@lru_cache(maxsize=1)
def _load_player_map() -> dict[str, str]:
    """
    Build a map: normalized player name -> TEAM code like 'NE', 'DET'.
    Reads DATA/nfl_depth_charts.csv.
    """
    roots = []
    try:
        roots.append(current_app.root_path)  # project root
    except Exception:
        roots.append(os.getcwd())

    # candidate paths
    candidates = []
    for root in roots:
        candidates.append(os.path.join(root, "DATA", "nfl_depth_charts.csv"))
        candidates.append(os.path.join(root, "..", "DATA", "nfl_depth_charts.csv"))

    path = next((p for p in candidates if os.path.exists(p)), None)
    mp: dict[str, str] = {}
    if not path:
        return mp

    try:
        df = pd.read_csv(path)
    except Exception:
        return mp

    # expect 'name' and 'team' columns
    name_col = next((c for c in df.columns if c.lower() == "name"), None)
    team_col = next((c for c in df.columns if c.lower() == "team"), None)
    if not name_col or not team_col:
        return mp

    for _, r in df.iterrows():
        nm = _norm_name(r.get(name_col))
        tm = str(r.get(team_col) or "").strip().upper()
        if nm and tm:
            mp[nm] = tm

            # Also add some common alternates (e.g., "aj brown" / "a j brown")
            nm_no_spaces = nm.replace(" ", "")
            mp.setdefault(nm_no_spaces, tm)

    return mp

def team_for_player(player_name: Optional[str]) -> Optional[str]:
    if not player_name:
        return None
    nm = _norm_name(player_name)
    if not nm:
        return None
    mp = _load_player_map()
    # exact
    if nm in mp:
        return mp[nm]
    # no-space fallback
    nm2 = nm.replace(" ", "")
    return mp.get(nm2)
