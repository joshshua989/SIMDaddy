
# utils/cache.py

from __future__ import annotations
import json, time
from pathlib import Path
from typing import Any, Optional

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def read_cache(path: Path, max_age_seconds: int) -> Optional[Any]:
    try:
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > max_age_seconds:
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def write_cache(path: Path, payload: Any) -> None:
    try:
        ensure_dir(path.parent)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        tmp.replace(path)
    except Exception:
        # cache errors must never break the app
        pass
