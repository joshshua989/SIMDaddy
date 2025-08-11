# utils/team_logo.py
"""
Resolve a local static logo URL for a given text by inferring the NFL team code.
If the logo file doesn't exist, return None (your template shows a placeholder).

Usage:
    from utils.team_logo import team_logo_url, logo_url_for_code

    url = team_logo_url("Chiefs WR Rashee Rice expected to ...")
    # -> "/static/logos/KC.svg" (if present) else None

    url = logo_url_for_code("NYJ")
    # -> "/static/logos/NYJ.svg" (if present) else None
"""
from __future__ import annotations
import os
from typing import Optional
from flask import current_app, url_for
from .team_lookup import infer_team_code


def _existing_static_logo_path(code: str) -> Optional[str]:
    """
    Check for an existing local logo file (SVG preferred, then PNG).
    Returns the web path (e.g., 'logos/NYJ.svg') or None.
    """
    try:
        root = current_app.root_path  # requires app context (route/view)
    except Exception:
        return None

    static_dir = os.path.join(root, "static", "logos")
    svg_fs = os.path.join(static_dir, f"{code}.svg")
    png_fs = os.path.join(static_dir, f"{code}.png")

    if os.path.exists(svg_fs):
        return f"logos/{code}.svg"
    if os.path.exists(png_fs):
        return f"logos/{code}.png"
    return None


def logo_url_for_code(code: Optional[str]) -> Optional[str]:
    """
    Given a team code, return a url_for('static', filename=...) if the logo exists locally.
    Else None (your template can show a placeholder).
    """
    if not code:
        return None
    rel = _existing_static_logo_path(code)
    if not rel:
        return None
    try:
        return url_for("static", filename=rel)
    except Exception:
        return None


def team_logo_url(text: Optional[str]) -> Optional[str]:
    """
    Convenience: infer code from text, then resolve to a static logo URL if present.
    """
    code = infer_team_code(text or "")
    return logo_url_for_code(code)
