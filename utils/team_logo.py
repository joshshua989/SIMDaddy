# utils/team_logo.py
from __future__ import annotations
from typing import Optional
from .team_logos import get_team_logo_url, normalize_code
from .team_lookup import infer_team_code

ESPN_LOGO_CDN = "https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png"  # code: canonical slug (lowercase)

def logo_url_for_code(code: Optional[str]) -> Optional[str]:
    """
    Prefer local /static logo; fallback to ESPN CDN using canonical lowercase slug.
    """
    canon = normalize_code(code)
    if not canon:
        return None

    local = get_team_logo_url(canon)
    if local:
        return local
    # Fallback: ESPN CDN
    return ESPN_LOGO_CDN.format(code=canon)

def team_logo_url(text: Optional[str]) -> Optional[str]:
    """
    Infer team code from free text, then resolve to a logo URL.
    """
    code = infer_team_code(text or "")
    return logo_url_for_code(code)
