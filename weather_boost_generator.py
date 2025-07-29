
# weather_boost_generator.py

from config import STADIUM_ENV_FILE, CLIMATE_PHASE, USE_FORECAST_WEATHER
from stat_loader import load_csv
from weather_estimator import estimate_weather_boost
from weather_estimator import get_noaa_forecast

forecast_cache = {}

def safe_float(val, default=0.0):
    try:
        if val is None or val == '' or str(val).lower() == 'none':
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def compute_weather_boost(stadium_profile, week, climate_phase, date):
    lat = stadium_profile.get("Latitude")
    lon = stadium_profile.get("Longitude")
    is_dome = stadium_profile.get("Dome", False)
    team = stadium_profile.get("Team", "")

    if is_dome:
        return 1.05, "Dome"

    if USE_FORECAST_WEATHER:
        # Convert date to datetime if needed
        from dateutil import parser
        if isinstance(date, str):
            game_date = parser.parse(date)
        else:
            game_date = date

        key = (lat, lon, game_date)

        if key in forecast_cache:
            forecast = forecast_cache[key]
        else:
            forecast = get_noaa_forecast(lat, lon, game_date)
            forecast_cache[key] = forecast

        boost = 1.0
        condition = "Unavailable"
        if forecast and not forecast.get("error"):
            temp = safe_float(forecast.get("temperature"), 60)
            wind_str = forecast.get("windSpeed", "10 mph")
            wind = int(wind_str.split(" ")[0]) if wind_str else 10
            short_forecast = forecast.get("shortForecast", "")
            condition = f"{temp}°F, {wind} wind, {short_forecast}"
            if temp < 35 or wind > 20:
                boost *= 0.9
            if "Snow" in short_forecast or "Sleet" in short_forecast:
                boost *= 0.85
            elif "Rain" in short_forecast or "Showers" in short_forecast:
                boost *= 0.92
        return round(boost, 3), condition

    return estimate_weather_boost(stadium_profile, week, climate_phase), "Climatology"

def build_weather_boost_map(schedule_df):
    env_df = load_csv(STADIUM_ENV_FILE)
    env_boost_map = {}

    for _, row in schedule_df.iterrows():
        week = row['Week']
        home_team = row['Home']
        date = row['Date']

        match = env_df[env_df['Team'] == home_team]
        if match.empty:
            boost, condition = 1.0, "Unknown"
            deep_penalty, short_penalty = 1.0, 1.0
        else:
            stadium_profile = match.iloc[0].to_dict()
            boost, condition = compute_weather_boost(stadium_profile, week, CLIMATE_PHASE, date)

            # Route-type penalties (only if forecast available)
            deep_penalty, short_penalty = 1.0, 1.0
            if USE_FORECAST_WEATHER:
                lat, lon = stadium_profile.get("Latitude"), stadium_profile.get("Longitude")
                game_date = date
                forecast = get_noaa_forecast(lat, lon, game_date)
                try:
                    wind = int(str(forecast.get("windSpeed", "0 mph")).split()[0])
                except Exception:
                    wind = 0
                precip = safe_float(forecast.get("precipitation"), 0)
                temp = safe_float(forecast.get("temperature"), 60)

                # Apply route-type aware weather penalties
                deep_penalty = 1.0
                if wind >= 15:
                    deep_penalty -= min(0.10, (wind - 14) * 0.01)
                if precip >= 50:
                    deep_penalty -= 0.10
                if temp < 32:
                    deep_penalty -= 0.05
                deep_penalty = max(0.75, deep_penalty)

                short_penalty = 1.0
                if precip >= 80:
                    short_penalty -= 0.03
                if temp < 25:
                    short_penalty -= 0.02
                short_penalty = max(0.90, short_penalty)

        if week not in env_boost_map:
            env_boost_map[week] = {}
        env_boost_map[week][home_team] = {
            "boost": round(boost, 3),
            "condition": condition,
            "deep_penalty": round(deep_penalty, 3),
            "short_penalty": round(short_penalty, 3)
        }

    return env_boost_map
