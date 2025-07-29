import pandas as pd
import os

def export_wr_weekly_summary(output_df: pd.DataFrame, week: int, output_dir="output/summaries"):
    os.makedirs(output_dir, exist_ok=True)

    summary_cols = [
        'week', 'wr_name', 'team', 'opp_team',
        'slot_weight', 'wide_weight', 'safety_weight', 'lb_weight',
        'base_pts', 'adj_pts', 'env_boost', 'game_script_boost'
    ]

    # 🧪 Only export if required columns exist
    if not all(col in output_df.columns for col in summary_cols):
        print("⚠️ Summary export skipped: missing columns.")
        return

    summary = output_df[summary_cols].copy()

    # Calculate Final Pts with boost multipliers
    summary['final_pts'] = (summary['adj_pts'] * summary['game_script_boost']).round(2)

    # Optional "Notes" column for scouting summary
    summary['Notes'] = summary.apply(generate_notes, axis=1)

    path = os.path.join(output_dir, f"wr_weekly_summary_{str(week).zfill(2)}.csv")
    summary.to_csv(path, index=False)
    print(f"📤 WR Weekly Summary saved to {path}")


def generate_notes(row):
    notes = []
    if row['env_boost'] > 1.02:
        notes.append("Dome or favorable weather")
    elif row['env_boost'] < 0.98:
        notes.append("Bad weather risk")

    if row['game_script_boost'] > 1.05:
        notes.append("Trailing game script boost")
    elif row['game_script_boost'] < 0.95:
        notes.append("Game script downgrade")

    return "; ".join(notes)
