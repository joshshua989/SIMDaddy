# YACulator: output_writer.py
import pandas as pd

def write_weekly_results(results, filename="weekly_projection_output.csv"):
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False)
