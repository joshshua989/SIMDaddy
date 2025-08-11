#!/usr/bin/env python3
"""
Trace where get_injury_reports() loads data from.

- Prints the module/file that defines get_injury_reports
- Shows the first ~120 lines of its source
- Monkey-patches pandas.read_csv and requests.get/post to log paths/URLs
- Calls get_injury_reports() and prints basic DataFrame info
"""

import os, sys, inspect, textwrap

# Ensure repo root on sys.path when script is run from repo root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ---- import your app + get_injury_reports (tries a few common locations) ----
def import_symbols():
    # Adjust/add candidates if your layout differs
    candidates = [
        ("app", "create_app"),
        ("app.__init__", "create_app"),
    ]
    create_app = None
    last_err = None
    for mod, sym in candidates:
        try:
            m = __import__(mod, fromlist=[sym])
            create_app = getattr(m, sym)
            break
        except Exception as e:
            last_err = e
    if create_app is None:
        raise RuntimeError(f"Could not import create_app from {candidates!r}: {last_err!r}")

    # Where might get_injury_reports live?
    gi_candidates = [
        "app.views.routes",
        "views.routes",
        "app.routes",
        "app.services.injuries",
        "services.injuries",
        "injuries",
    ]
    get_injury_reports = None
    gi_mod = None
    last_err = None
    for path in gi_candidates:
        try:
            m = __import__(path, fromlist=["get_injury_reports"])
            if hasattr(m, "get_injury_reports"):
                get_injury_reports = getattr(m, "get_injury_reports")
                gi_mod = m
                break
        except Exception as e:
            last_err = e

    if get_injury_reports is None:
        raise RuntimeError(f"Could not import get_injury_reports from {gi_candidates!r}: {last_err!r}")

    # optional helper
    team_logo_url = getattr(gi_mod, "team_logo_url", None)
    return create_app, get_injury_reports, team_logo_url

def preview_source(fn, lines=120):
    try:
        src = inspect.getsource(fn)
        src = "\n".join(src.splitlines()[:lines])
        return src
    except Exception:
        return "<unable to read function source>"

def file_of(obj):
    try:
        return inspect.getsourcefile(obj) or inspect.getfile(obj)
    except Exception:
        return "<unknown>"

# ---- monkey-patches to capture data sources ----
captured = {"read_csv": [], "http": []}

def patch_read_csv():
    try:
        import pandas as pd
    except Exception:
        return None
    real = pd.read_csv
    def wrapper(*args, **kwargs):
        path = str(args[0]) if args else "<no-arg>"
        captured["read_csv"].append(path)
        print(f"[TRACE] pandas.read_csv -> {path}")
        return real(*args, **kwargs)
    pd.read_csv = wrapper
    return ("pandas.read_csv", real)

def patch_requests():
    try:
        import requests
    except Exception:
        return None
    real_get = requests.get
    real_post = requests.post
    def wrap(method_name, real):
        def inner(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "<no-url>")
            captured["http"].append(f"{method_name} {url}")
            print(f"[TRACE] requests.{method_name} -> {url}")
            return real(*args, **kwargs)
        return inner
    requests.get = wrap("get", real_get)
    requests.post = wrap("post", real_post)
    return [("requests.get", real_get), ("requests.post", real_post)]

def restore(patches):
    for name, real in patches:
        pkg, attr = name.split(".")
        mod = __import__(pkg)
        setattr(mod, attr, real)

def main():
    from pprint import pprint
    create_app, get_injury_reports, team_logo_url = import_symbols()

    print("=== Function location ===")
    print("module:", get_injury_reports.__module__)
    print("file  :", file_of(get_injury_reports))
    print("\n=== Function source (preview) ===")
    print(textwrap.indent(preview_source(get_injury_reports), "  "))

    # Patches
    patches = []
    r1 = patch_read_csv()
    if r1: patches.append(r1)
    r2s = patch_requests()
    if r2s:
        patches.extend(r2s)

    # Run in app context so any config/env is available
    app = create_app()
    with app.app_context():
        try:
            df = get_injury_reports()
        except Exception as e:
            print("\n[ERROR] get_injury_reports() raised an exception:")
            print(" ", repr(e))
            restore([p for p in patches if p])
            return

    print("\n=== DataFrame snapshot ===")
    try:
        import pandas as pd  # noqa
        print("rows:", 0 if df is None else len(df))
        if df is not None and hasattr(df, "columns"):
            print("columns:", list(df.columns))
            print(df.head(3).to_string(index=False))
    except Exception as e:
        print("Could not print DataFrame info:", repr(e))

    print("\n=== Captured sources ===")
    if captured["read_csv"]:
        print("CSV files:")
        for p in captured["read_csv"]:
            print(" -", p)
    if captured["http"]:
        print("HTTP calls:")
        for u in captured["http"]:
            print(" -", u)
    if not captured["read_csv"] and not captured["http"]:
        print("No CSV or HTTP activity captured. Source might be a DB or in-memory.")

    # cleanup
    restore([p for p in patches if p])

if __name__ == "__main__":
    main()
