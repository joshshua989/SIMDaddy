# YACulator: quality_control.py
import os
import pandas as pd
from config import *

def check_file(file):
    if not os.path.exists(file):
        return f"❌ Missing: {file}"
    try:
        df = pd.read_csv(file)
        if df.empty:
            return f"⚠️ Empty: {file}"
    except Exception as e:
        return f"❌ Error reading {file}: {e}"
    return f"✅ OK: {file}"

def run_qc():
    files = [BLENDED_WR_FILE, BLENDED_DB_FILE, SCHEDULE_FILE, COVERAGE_TAGS_FILE, ROSTER_FILE]
    for file in files:
        print(check_file(file))

if __name__ == "__main__":
    run_qc()
