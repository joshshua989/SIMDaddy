import pandas as pd

# --- USER PARAMETERS ---
INPUT_CSV = "output/summaries/wr_weekly_summary_01.csv"    # Path to your SIMDaddy WR sim output CSV
BOOM_THRESHOLD = 18                              # Define "boom" week (e.g., 18+ fantasy points)
PLAYOFF_WEEKS = [15, 16, 17]                     # Weeks considered as fantasy playoffs

# --- LOAD DATA ---
df = pd.read_csv(INPUT_CSV)

# --- GENERATE REPORT ---
def boom_week_report(
    df,
    fp_col="proj_fantasy_pts",
    boom_thresh=BOOM_THRESHOLD,
    playoff_weeks=PLAYOFF_WEEKS,
    context_cols=("environment_boost", "notes")
):
    results = []
    grouped = df.groupby(['player_id', 'player_name', 'team'])
    for (pid, pname, team), g in grouped:
        boom_weeks = g[g[fp_col] >= boom_thresh]['week'].tolist()
        playoff_boom_weeks = [w for w in boom_weeks if w in playoff_weeks]
        # Optional context
        avg_playoff_env = (
            g[g['week'].isin(playoff_boom_weeks)]['environment_boost'].mean()
            if playoff_boom_weeks else None
        )
        playoff_notes = (
            " | ".join(g[g['week'].isin(playoff_boom_weeks)]['notes'].dropna().astype(str))
            if playoff_boom_weeks else ""
        )
        results.append({
            'Player Name': pname,
            'Team': team,
            'Total Boom Weeks': len(boom_weeks),
            'Playoff Boom Weeks': len(playoff_boom_weeks),
            'Boom Weeks (List)': boom_weeks,
            'Playoff Boom Weeks (List)': playoff_boom_weeks,
            'Avg Playoff Env Boost': avg_playoff_env,
            'Playoff Notes': playoff_notes
        })
    boom_df = pd.DataFrame(results)
    # Sort by playoff upside, then total boom weeks
    boom_df = boom_df.sort_values(['Playoff Boom Weeks', 'Total Boom Weeks'], ascending=False)
    return boom_df

# --- RUN REPORT ---
boom_week_summary = boom_week_report(df)
boom_week_summary.to_csv("wr_best_ball_boom_week_report.csv", index=False)
print(boom_week_summary.head(20))
