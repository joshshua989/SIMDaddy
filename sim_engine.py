
# sim_engine.py

import os
import csv
import pandas as pd
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count

from config import (
    NFL_SCHEDULE_2025_FILE,
    WR_STATS_2024_FILE,
    DB_ALIGNMENT_FILE,
    DEF_COVERAGE_TAGS_FILE,
    EXPORT_FULL_SEASON_FILE,
    EXPORT_TEST_WEEK_FILE,
    STADIUM_ENV_FILE,
    WR_PROP_MARKET_FILE,
    ROSTER_2025_FILE,
    PROJECTION_SOURCE_TOGGLE,
    USE_FORECAST_WEATHER
)
from stat_loader import load_csv
from matchup_simulator import load_db_alignment, load_wr_stats, project_wr_week
from weather_estimator import get_noaa_forecast
from report_generator import export_wr_weekly_summary
from html_generator import export_week_html
from load_multipliers import load_all_multipliers


# -------------------------------
# PARSE SCHEDULE
# -------------------------------

#Defines function to parse and format the NFL schedule DataFrame.
def parse_schedule(schedule_df):
    #Initializes an empty list to store parsed game dictionaries.
    parsed = []
    #Iterates through each row of the schedule DataFrame.
    for _, row in schedule_df.iterrows():
        #For each row, it tries to extract and format relevant schedule fields and appends the parsed dict to the list.
        #If parsing fails, it logs an error and continues.
        try:
            week = int(row["Week"])

            #TODO: get the real hour from the schedule (if available, e.g., from a Time column)
            #date_str = row['Date']  # "2025-09-08"
            #time_str = row.get('Time', '13:00')  # fallback to 1 PM
            #game_datetime = datetime.strptime(date_str + ' ' + time_str, "%Y-%m-%d %H:%M")

            full_date = f"{row['Date']}, 2025"
            game_date = datetime.strptime(full_date, "%B %d, %Y")
            parsed.append({
                "Week": week,
                "Team": row["Home"],
                "Opponent": row["Visitor"],
                "Stadium": row["Home"],
                "Date": game_date.strftime("%Y-%m-%d"),
                "Time": row["Time"],
                "ProjectedHomeScore": row.get("ProjectedHomeScore"),
                "ProjectedAwayScore": row.get("ProjectedAwayScore")
            })
        except Exception as e:
            print(f"\n⚠️ Error parsing schedule row: {e}")
            continue

    #Returns the parsed schedule as a new DataFrame.
    return pd.DataFrame(parsed)

# -------------------------------
# BUILD_DEF_TEAM_COVERAGE_MAP
# -------------------------------

#Defines the function to process coverage tags and build the man/zone mapping.
def build_def_team_coverage_map(coverage_df):
    #Initializes an empty dictionary to store the map.
    def_team_coverage_map = {}
    #Loops through each row of the coverage DataFrame.
    for _, row in coverage_df.iterrows():
        try:
            week = row['week']
            team = row['team']
            man = float(row.get("man_coverage_rate", 0))
            zone = float(row.get("zone_coverage_rate", 0))
            def_team_coverage_map.setdefault(week, {})[team] = {
                "man": man,
                "zone": zone
            }
        except Exception as e:
            print(f"\n⚠️ Error processing coverage row: {e} -- {row}")

    #Returns the completed week-by-team coverage scheme map.
    return def_team_coverage_map

# -------------------------------
# LOG WEATHER FORECAST
# -------------------------------

#Defines the function to log weather forecast and boost details for each game to a CSV.
def log_weather_forecast(week, stadium, lat, lon, game_date, forecast_data, weather_boost,
                         output_path="weather_log.csv"):
    #Defines the CSV columns to log.
    fieldnames = [
        "week", "stadium", "game_date", "lat", "lon",
        "forecast_time", "temperature", "windSpeed", "precipitation", "shortForecast",
        "weather_boost"
    ]
    #Constructs the row to log using provided values and fields from forecast_data.
    row = {
        "week": week,
        "stadium": stadium,
        "game_date": game_date.strftime('%Y-%m-%d'),
        "lat": lat,
        "lon": lon,
        "forecast_time": forecast_data.get("forecast_time"),
        "temperature": forecast_data.get("temperature"),
        "windSpeed": forecast_data.get("windSpeed"),
        "precipitation": forecast_data.get("precipitation"),
        "shortForecast": forecast_data.get("shortForecast"),
        "weather_boost": weather_boost
    }
    #Checks if the file exists (to write headers if new), opens the file in append mode, and writes the log row.
    write_header = not os.path.exists(output_path)
    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

# -------------------------------
# BUILD_FORECAST_WEATHER_BOOST_MAP
# -------------------------------

#Defines the function that constructs weather/environment adjustment values per game.
def build_forecast_weather_boost_map(schedule_df, env_profile_df):
    #Initializes an empty dictionary to store weather boost values.
    env_boost_map = {}
    #Iterates through every scheduled game in the schedule DataFrame.
    for _, row in schedule_df.iterrows():
        try:
            #Extracts week, team, stadium, and parses the date string to a datetime object for the game.
            week = row['Week']
            team = row['Team']
            stadium = row['Stadium']
            game_date = datetime.strptime(row['Date'], "%Y-%m-%d") + timedelta(hours=13)

            #Finds the stadium’s environment profile by matching the team.
            env_profile = env_profile_df[env_profile_df['Team'] == stadium]
            #If not found, logs a warning and skips this game.
            if env_profile.empty:
                print(f"\n❌ No environment profile for team: {stadium}")
                continue

            #Extracts latitude and longitude for weather lookup.
            lat = env_profile.iloc[0]['Latitude']
            lon = env_profile.iloc[0]['Longitude']
            #Initializes weather boost and forecast data variables.
            weather_boost = 0
            forecast_data = {}

            #If weather forecasts are enabled, calls NOAA and applies penalties for heavy precipitation, cold, or wind.
            #If not available, sets up empty dummy forecast data.
            if USE_FORECAST_WEATHER:
                forecast_data = get_noaa_forecast(lat, lon, game_date)

                if forecast_data and not forecast_data.get("error"):
                    precip = float(forecast_data.get("precipitation") or 0)

                    # Apply a penalty that scales with the chance of rain
                    # At 50% rain: penalty = -0.75
                    # At 80% rain: penalty = -1.2
                    # At 100% rain: penalty = -1.5
                    weather_boost -= (precip / 100) * 1.5  # Max -1.5 if 100% precip

                    try:
                        # At 30°F: penalty = -0.5
                        # At 20°F: penalty = -1.5 (max)
                        # At 34°F: penalty = -0.1
                        # At 40°F: no penalty
                        temperature = float(forecast_data.get("temperature", 100))
                        if temperature < 35:
                            # Penalty gets bigger as temp drops. E.g., -1.0 at 25°F, -1.5 at 15°F.
                            weather_boost -= min(1.5, (35 - temperature) * 0.1)  # cap at -1.5
                    except Exception as e:
                        print(f"⚠️ Temp parsing error: {e}")

                    try:
                        #At 10 mph: penalty = 0
                        #At 15 mph: penalty = -0.5
                        #At 20 mph: penalty = -1.0 (cap)
                        wind_str = forecast_data.get("windSpeed", "0 mph")
                        wind = int(wind_str.split(" ")[0]) if wind_str else 0
                        if wind >= 10:
                            # Penalty scales up as wind increases past 10 mph, capped at -1.0 for very windy
                            weather_boost -= min(1.0, ((wind - 10) * 0.1))
                    except Exception as e:
                        print(f"⚠️ Wind parsing error: {e}")

                else:
                    forecast_data = {
                        "forecast_time": None,
                        "temperature": None,
                        "windSpeed": None,
                        "precipitation": None,
                        "shortForecast": "N/A"
                    }

            #Logs the weather forecast and saves the weather boost for this team/week to the map.
            log_weather_forecast(week, stadium, lat, lon, game_date, forecast_data, weather_boost)
            env_boost_map[(week, team)] = weather_boost

        except Exception as e:
            print(f"\n⚠️ Error processing weather boost for {row}: {e}")

    #Returns the full mapping of (week, team) to weather boost.
    return env_boost_map

# -------------------------------
# SIMULATE_FOR_WEEK
# -------------------------------

def simulate_for_week(args):
    week, wr_map, schedule_df, db_map, def_coverage_map, env_boost_map, simulations, multipliers = args
    penalty_cache = {}
    results = []
    for wr in wr_map.values():
        key = (week, wr.team)
        if key not in penalty_cache:
            penalty_cache[key] = None
        proj = project_wr_week(
            wr, week, schedule_df, db_map, def_coverage_map,
            simulations=simulations,
            precomputed=penalty_cache[key],
            env_boost_map=env_boost_map,
            multipliers=multipliers
        )
        if proj:
            results.append(proj)

        week_df = pd.DataFrame(results)

        # Save game script report
        report_cols = ['wr_name', 'team', 'opp_team', 'week', 'base_pts', 'adj_pts', 'game_script_boost']
        if all(col in week_df.columns for col in report_cols):
            week_df[report_cols].sort_values('game_script_boost', ascending=False).to_csv(
                f"output/game_script_report_week{week}.csv", index=False)
            print(f"📝 Game script report saved to output/game_script_report_week{week}.csv")

        # Save HTML visualizer
        export_week_html(week_df, week)

    return results

# -------------------------------
# RUN SEASON SIMULATION
# -------------------------------

def run_season_simulation(output_file=None, simulations=100):
    print(f'\n1. Loading schedule...')
    raw_schedule_df = load_csv(NFL_SCHEDULE_2025_FILE)
    schedule_df = parse_schedule(raw_schedule_df)

    print(f'\n2. Loading WR stats...')
    wr_map = load_wr_stats(WR_STATS_2024_FILE)

    print(f'\n3. Loading DB alignment...')
    db_map = load_db_alignment(DB_ALIGNMENT_FILE)

    print(f'\n4. Loading coverage tags...')
    coverage_df = load_csv(DEF_COVERAGE_TAGS_FILE)
    def_coverage_map = build_def_team_coverage_map(coverage_df)

    print(f'\n5. Loading environment profile...')
    env_profile_df = load_csv(STADIUM_ENV_FILE)
    env_boost_map = build_forecast_weather_boost_map(schedule_df, env_profile_df)

    print(f'\n6. Simulating season in parallel using {cpu_count()} cores...')
    multipliers = load_all_multipliers()
    args = [
        (week, wr_map, schedule_df, db_map, def_coverage_map, env_boost_map, simulations, multipliers)
        for week in sorted(schedule_df['Week'].unique())
    ]

    with Pool(cpu_count()) as pool:
        week_results = pool.map(simulate_for_week, args)

    results = [r for week in week_results for r in week if r]

    output_df = pd.DataFrame(results)
    out_file = output_file or EXPORT_FULL_SEASON_FILE
    output_df.to_csv(out_file, index=False)
    print(f"\n✅ Full-season projections saved to {out_file}")

    agg_fields = {
        'base_pts': 'mean',
        'adj_pts': ['sum', 'mean'],
        'final_pts': 'mean',
        'game_script_boost': 'mean' if 'game_script_boost' in output_df.columns else 'mean',
    }

    if 'adj_pts_p50' in output_df.columns:
        agg_fields['adj_pts_p50'] = 'mean'

    team_summary = output_df.groupby(['team']).agg(agg_fields).reset_index()
    team_summary.columns = ['Team', 'Avg Base Pts', 'Total Adj Pts', 'Avg Adj Pts', 'Avg Final Pts',
                            'Avg Script Boost'] + (['Avg Median Pts'] if 'adj_pts_p50' in output_df.columns else [])
    team_summary.to_csv("output/team_projection_summary.csv", index=False)
    print("📊 Team summary saved to output/team_projection_summary.csv")

# -------------------------------
# RUN WEEK SIMULATION
# -------------------------------

def run_week_simulation(week, output_file=None, simulations=100):
    multipliers = load_all_multipliers()

    #Loads the raw schedule CSV into a DataFrame.
    raw_schedule_df = load_csv(NFL_SCHEDULE_2025_FILE)
    #Parses the schedule DataFrame to normalize/format it for use.
    schedule_df = parse_schedule(raw_schedule_df)

    #Loads WR stats from the 2024 stats CSV into a dictionary or mapping of WR objects.
    wr_map = load_wr_stats(WR_STATS_2024_FILE)
    #Prints which teams, opponents, and number of games are scheduled for the week (for debugging/logging).
    print("\nSchedule teams for week", week, ":", schedule_df[schedule_df['Week'] == week]['Team'].tolist())
    print("\nSchedule opponents for week", week, ":", schedule_df[schedule_df['Week'] == week]['Opponent'].tolist())
    print("\nNumber of schedule rows for week", week, ":", len(schedule_df[schedule_df['Week'] == week]))

    #Loads the DB (defensive back) alignment data for the week from the CSV into a mapping or dictionary.
    db_map = load_db_alignment(DB_ALIGNMENT_FILE)

    #Loads the defense coverage scheme CSV into a DataFrame (contains man/zone rates per team/week).
    coverage_df = load_csv(DEF_COVERAGE_TAGS_FILE)
    #Processes the coverage DataFrame to build a mapping of teams/weeks to their man/zone scheme rates.
    def_coverage_map = build_def_team_coverage_map(coverage_df)

    #Loads stadium environment profile data (lat/lon, dome, turf, etc.) into a DataFrame.
    env_profile_df = load_csv(STADIUM_ENV_FILE)
    #Builds a map of environment/weather boosts for each team/week using the schedule and stadium environment data.
    env_boost_map = build_forecast_weather_boost_map(schedule_df, env_profile_df)

    #Initializes an empty list to hold the simulation results for each WR, and a cache for DB penalties (for efficiency).
    results = []
    penalty_cache = {}

    #Loops over every WR, prints basic info, gets a team/week cache key, then runs project_wr_week() with all context.
    #Appends the result if not empty.
    for i, wr in enumerate(wr_map.values()):
        print(f"START WR: {wr.name} ({wr.team})")
        key = (week, wr.team)
        if key not in penalty_cache:
            penalty_cache[key] = None

        wr_performance_projections = project_wr_week(
            wr, week, schedule_df, db_map, def_coverage_map,
            simulations=simulations,
            precomputed=penalty_cache[key],
            env_boost_map=env_boost_map,
            multipliers=multipliers
        )
        if wr_performance_projections:
            results.append(wr_performance_projections)

    output_df = pd.DataFrame(results)
    out_file = output_file or EXPORT_TEST_WEEK_FILE
    output_df.to_csv(out_file, index=False)
    print(f"✅ Test Week {week} projections saved to {out_file}")

    # ✅ Generate game script report
    if 'game_script_boost' in output_df.columns:
        cols = ['wr_name', 'team', 'opp_team', 'week', 'base_pts', 'adj_pts', 'game_script_boost', 'env_boost']
        game_script_df = output_df[cols].copy()
        game_script_df['final_pts'] = (game_script_df['adj_pts'] * game_script_df['game_script_boost']).round(2)
        game_script_df.sort_values('game_script_boost', ascending=False).to_csv(
            f"output/game_script_report_week{week}.csv", index=False)
        print(f"📝 Game script report saved to output/game_script_report_week{week}.csv")

    # Load DK props and roster for player matching
    try:
        prop_df = pd.read_csv(WR_PROP_MARKET_FILE)
        roster_df = pd.read_csv(ROSTER_2025_FILE)
    except FileNotFoundError:
        print("❌ Could not find prop or roster file.")
        prop_df = pd.DataFrame()
        roster_df = pd.DataFrame()

    # Clean and match players
    def clean_name(name):
        return name.lower().replace(".", "").replace("-", "").replace("'", "").replace(" ", "")

    if not prop_df.empty and not roster_df.empty:
        roster_df["clean_name"] = roster_df["full_name"].apply(clean_name)
        prop_df["player_clean"] = prop_df["player"].apply(clean_name)

        prop_pivot = prop_df.pivot_table(index="player_clean", columns="market", values="value",
                                         aggfunc="first").reset_index()
        prop_df_grouped = prop_df.groupby("player_clean").first().reset_index()
        prop_pivot["player"] = prop_df_grouped["player"]

        merged = pd.merge(roster_df, prop_pivot, on="clean_name", how="inner")

        # Fantasy scoring logic
        merged["market_rec"] = merged.get("player_receptions", 0) + 0.5
        merged["market_yds"] = merged.get("player_receiving_yards", 0) + 2.0
        merged["market_td"] = 0.4  # default if odds missing

        # Map prop points to final projection df
        name_map = dict(
            zip(merged["gsis_id"], merged[["market_rec", "market_yds", "market_td", "player"]].values.tolist()))

        def map_market_projection(row):
            pid = row.get("player_id")
            if pid in name_map:
                rec, yds, td, _ = name_map[pid]
                return rec + yds * 0.1 + td * 6.0
            return None

        output_df["market_ppr"] = output_df.apply(map_market_projection, axis=1)
        output_df["model_ppr"] = output_df["final_pts"]
        output_df["blend_ppr"] = output_df[["model_ppr", "market_ppr"]].mean(axis=1)

        # Apply source toggle
        def select_proj(row):
            if PROJECTION_SOURCE_TOGGLE == "market" and not pd.isna(row["market_ppr"]):
                return row["market_ppr"], "market"
            elif PROJECTION_SOURCE_TOGGLE == "blend" and not pd.isna(row["market_ppr"]):
                return row["blend_ppr"], "blend"
            else:
                return row["model_ppr"], "model"

        output_df[["final_proj", "proj_source"]] = output_df.apply(lambda row: pd.Series(select_proj(row)), axis=1)

        print(f"📦 Projections updated with {PROJECTION_SOURCE_TOGGLE} source.")
    else:
        output_df["market_ppr"] = None
        output_df["model_ppr"] = output_df["final_pts"]
        output_df["blend_ppr"] = output_df["final_pts"]
        output_df["final_proj"] = output_df["final_pts"]
        output_df["proj_source"] = "model"

    # ✅ Export Weekly WR Summary
    export_wr_weekly_summary(output_df, week)

    export_week_html(output_df, week)

    return results
