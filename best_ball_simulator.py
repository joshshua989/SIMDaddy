import pandas as pd
import glob
from collections import Counter

# --- CONFIG: Edit this section for your league ---
n_starters = 3  # Number of WR starters in best ball each week

# Put your drafted WRs here!
my_wr_list = [
    "Ja'Marr Chase", "Amon-Ra St. Brown", "Justin Jefferson",
    "Garrett Wilson", "CeeDee Lamb", "Tyreek Hill", "Puka Nacua"
]

# --- LOAD DATA ---
# If you have multiple weeks, put all CSVs in output/summaries/ with the pattern below.
files = sorted(glob.glob("output/summaries/wr_weekly_summary_*.csv"))
if not files:
    files = ["wr_weekly_summary_01.csv"]  # fallback

all_weeks = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

# If week column is missing (some exports), add it from the filename as a fallback
if 'week' not in all_weeks.columns:
    for i, f in enumerate(files, 1):
        all_weeks.loc[all_weeks.index // len(files) == i-1, 'week'] = i
    all_weeks['week'] = all_weeks['week'].astype(int)

# --- FILTER TO YOUR ROSTER ---
team_df = all_weeks[all_weeks["wr_name"].isin(my_wr_list)].copy()

# --- BEST BALL SCORING ---
weekly_results = []
for week in sorted(team_df['week'].unique()):
    week_df = team_df[team_df['week'] == week].sort_values("final_pts", ascending=False)
    top_wr = week_df.head(n_starters)
    total = top_wr["final_pts"].sum()
    weekly_results.append({
        "week": week,
        "score": total,
        "starters": list(top_wr["wr_name"]),
        "starter_points": list(top_wr["final_pts"])
    })

weekly_df = pd.DataFrame(weekly_results)

# --- OUTPUT ---
print("Weekly best ball scores:\n", weekly_df)
print("\nSeason total:", weekly_df["score"].sum())
print("Mean weekly score:", weekly_df["score"].mean())

# WR starter appearance count
starter_counts = Counter()
for starters in weekly_df["starters"]:
    for wr in starters:
        starter_counts[wr] += 1
print("\nWR Starter Appearances:")
for wr, count in starter_counts.most_common():
    print(f"{wr}: {count}")

# Save to CSV
weekly_df.to_csv("best_ball_simulation_results.csv", index=False)
print("\n✅ Results saved to best_ball_simulation_results.csv")
