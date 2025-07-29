# YACulator: stat_loader.py
import pandas as pd

def load_csv(filepath):
    import os
    df = pd.read_csv(filepath)
    sample = df.iloc[0]

    print(f"\n(SAMPLE) \n{os.path.normpath(filepath)}:")
    for col in df.columns:
        val = sample[col]
        print(f"🔹 {col}: {val}")

    return df
