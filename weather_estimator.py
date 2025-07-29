
# weather_estimator.py

import requests
from datetime import datetime, timedelta
from config import NOAA_POINTS_BASE_URL

CLIMATE_PHASE_MODIFIERS = {
    "ElNino": {
        "Northeast": 1.1,
        "Midwest": 1.1,
        "Southwest": 0.95
    },
    "LaNina": {
        "Northwest": 1.1,
        "Southeast": 1.1,
        "Midwest": 0.95
    },
    "Neutral": {
        "Northeast": 1.0,
        "Midwest": 1.0,
        "Southwest": 1.0,
        "Southeast": 1.0,
        "Northwest": 1.0
    }
}

def estimate_weather_boost(stadium_row: dict, week: int, climate_phase: str = "Neutral") -> float:
    """
    Estimate weather risk boost based on stadium attributes, week, and climate phase.
    Returns a multiplicative boost (e.g., 1.05 means +5%).
    """

    # Base boost
    boost = 1.0

    # 1. Indoor stadiums
    if stadium_row.get("Dome", False):
        return 1.05  # constant safe indoor boost

    # 2. Base seasonal penalty
    week_modifier = 1.0
    if week >= 12:
        if stadium_row.get("ColdProne", False):
            week_modifier *= 0.95
        if stadium_row.get("WindProne", False):
            week_modifier *= 0.97
    elif week >= 8:
        if stadium_row.get("ColdProne", False):
            week_modifier *= 0.98

    boost *= week_modifier

    # 3. Altitude penalty
    if stadium_row.get("HighAltitude", False):
        boost *= 0.98  # simulate thinner air or endurance drain

    # 4. Turf type and humidity modifiers
    turf = stadium_row.get("TurfType", "").lower()
    humidity_control = stadium_row.get("HumidityControl", "").lower()

    if "natural" in turf:
        boost *= 0.99  # slightly less predictable surface
    elif "hybrid" in turf:
        boost *= 1.00  # neutral
    elif "artificial" in turf:
        boost *= 1.02  # slightly faster play surfaces

    if "yes" in humidity_control:
        boost *= 1.01
    elif "partial" in humidity_control:
        boost *= 1.00
    else:
        boost *= 0.99  # potentially more fatigue or error-prone

    # 5. Climate pattern modifiers
    state = stadium_row.get("State", "")
    climate_region = classify_climate_region(state)
    boost *= CLIMATE_PHASE_MODIFIERS.get(climate_phase, {}).get(climate_region, 1.0)

    return round(boost, 3)


def classify_climate_region(state: str) -> str:
    """Classify U.S. state into simplified regional climate categories."""
    state = state.upper()
    northeast = {"NY", "PA", "MA", "NJ", "CT", "RI", "NH", "VT", "ME"}
    midwest = {"IL", "OH", "MI", "WI", "IN", "IA", "MN", "MO", "NE", "KS"}
    southeast = {"FL", "GA", "SC", "NC", "AL", "TN", "MS", "KY", "VA"}
    southwest = {"AZ", "NM", "TX", "OK"}
    northwest = {"WA", "OR", "ID", "MT", "WY", "CO", "UT"}

    if state in northeast:
        return "Northeast"
    if state in midwest:
        return "Midwest"
    if state in southeast:
        return "Southeast"
    if state in southwest:
        return "Southwest"
    if state in northwest:
        return "Northwest"
    return "Neutral"

#Defines the function to fetch a forecast from the NOAA API for a specific lat/lon and game time.
def get_noaa_forecast(lat, lon, game_date):
    try:
        #Step 1: Builds the points API URL, requests location metadata, and extracts the hourly forecast URL.
        points_url = f"{NOAA_POINTS_BASE_URL}/{lat},{lon}"
        meta = requests.get(points_url, timeout=10).json()
        forecast_url = meta['properties']['forecastHourly']

        #Step 2: Fetches hourly forecast data and gets the list of hourly periods.
        forecast_data = requests.get(forecast_url, timeout=10).json()
        periods = forecast_data['properties']['periods']

        # Step 3: Finds the forecast period whose start time is closest to the game time.
        closest = None
        min_diff = timedelta(days=99)

        for p in periods:
            forecast_time = datetime.fromisoformat(p['startTime'][:-6])
            diff = abs(forecast_time - game_date)
            if diff < min_diff:
                min_diff = diff
                closest = p

        #Returns the weather data from the closest forecast period as a dictionary.
        if closest:
            return {
                "forecast_time": closest['startTime'],
                "temperature": closest['temperature'],
                "windSpeed": closest['windSpeed'],
                "precipitation": closest.get('probabilityOfPrecipitation', {}).get('value', None),
                "shortForecast": closest['shortForecast']
            }

    except Exception as e:
        return {"error": str(e)}

    #Fallback return if no forecast was found
    return {
        "forecast_time": None,
        "temperature": None,
        "windSpeed": None,
        "precipitation": None,
        "shortForecast": "No forecast available"
    }
