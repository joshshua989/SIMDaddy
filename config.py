# config.py

from pathlib import Path
import os

# -------------------------------
# Environment Control
# -------------------------------
ENVIRONMENT = "DEV"
CURRENT_WEEK = 1
FILENAME_SUFFIX = "_v1_test"

# -------------------------------
# File Paths
# -------------------------------
DATA_DIR = Path("DATA")
PLAYER_PROFILER_DIR = Path("player_profiler_data")
NFL_SCHEDULES_DIR = Path("nfl_schedules")
NFL_ROSTER_DIR = Path("rosters")

ROSTER_2025_FILE = DATA_DIR / NFL_ROSTER_DIR / "NFL_ROSTER_2025.csv"
NFL_SCHEDULE_2025_FILE = DATA_DIR / NFL_SCHEDULES_DIR / "NFL_SCHEDULE_2025.csv"
NFL_SCHEDULE_2024_FILE = DATA_DIR / NFL_SCHEDULES_DIR / "NFL_SCHEDULE_2024.csv"
WR_STATS_2024_FILE = DATA_DIR / PLAYER_PROFILER_DIR / "WR_STATS_2024.csv"
DB_ALIGNMENT_FILE = DATA_DIR / PLAYER_PROFILER_DIR / "DB_STATS_2022_2023_2024.csv"
BLENDED_WR_FILE = DATA_DIR / PLAYER_PROFILER_DIR / "BLENDED_WR_STATS.csv"
BLENDED_DB_FILE = DATA_DIR / PLAYER_PROFILER_DIR / "BLENDED_DB_STATS.csv"
DEF_COVERAGE_TAGS_FILE = DATA_DIR / "DEF_TEAM_COVERAGE_TAGS.csv"
STADIUM_ENV_FILE = DATA_DIR / "STADIUM_ENVIRONMENT_PROFILES.csv"
WR_PROP_MARKET_FILE = DATA_DIR / "wr_prop_market.csv"

EXPORT_HTML_DIR = Path("html_output")
EXPORT_FULL_SEASON_FILE = f"season_projection_output{FILENAME_SUFFIX}.csv"
EXPORT_TEST_WEEK_FILE = f"test_week_projection{FILENAME_SUFFIX}.csv"

# -------------------------------
# Game Script Settings
# -------------------------------
USE_GAME_SCRIPT_BOOST = True
USE_ADVANCED_GAME_SCRIPT_MODEL = True

# -------------------------------
# Alignment Logic
# -------------------------------
USE_SOFT_ALIGNMENT = True

# -------------------------------
# Coverage Scheme Logic
# -------------------------------
DEFAULT_MAN_ZONE_BLEND = True

# -------------------------------
# Projection Weights
# -------------------------------
PROJECTION_WEIGHTS = {
    "slot": 1.0,
    "wide": 1.0,
    "safety": 0.2,
    "lb": 0.1
}

# -------------------------------
# Multi-Year Blend Decay
# -------------------------------
BLEND_WEIGHTS = {
    2024: 0.5,
    2023: 0.3,
    2022: 0.2
}

# -------------------------------
# MULTIPLIER CSVs
# -------------------------------
TEAM_SCRIPT_RESPONSE_CSV = "DATA/multipliers/team_script_response.csv"
WR_SCRIPT_SENSITIVITY_CSV = "DATA/multipliers/wr_script_sensitivity.csv"
PACE_MULTIPLIER_CSV = "DATA/multipliers/pace_multiplier.csv"
DEF_PASS_RATE_ALLOWED_CSV = "DATA/multipliers/def_pass_rate_allowed.csv"
QB_SCRIPT_RESPONSE_CSV = "DATA/multipliers/qb_script_response.csv"

ROLE_MULTIPLIER = {
    "WR1": 1.0,
    "WR2": 0.8,
    "WR3": 0.5,
    "Slot": 0.7
}

# -------------------------------
# Weather Settings
# -------------------------------
NOAA_POINTS_BASE_URL = "https://api.weather.gov/points"
FORCE_DOME_NO_WEATHER_PENALTY = True
CLIMATE_PHASE = "ElNino"
USE_FORECAST_WEATHER = True

# -------------------------------
# Projection Source Toggle
# -------------------------------
PROJECTION_SOURCE_TOGGLE = "model"

# -------------------------------
# Logging + Quality Control
# -------------------------------
ENABLE_QUALITY_CONTROL = True
ENABLE_GAME_SCRIPT_EXPLANATION = True
ENABLE_ENVIRONMENT_EXPLANATION = False

# ==========================================================
# 🔐 Flask Config Class for App/Auth
# ==========================================================

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///simdaddy.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # reCAPTCHA
    RECAPTCHA_PUBLIC_KEY = os.getenv("RECAPTCHA_PUBLIC_KEY", "your-recaptcha-site-key")
    RECAPTCHA_PRIVATE_KEY = os.getenv("RECAPTCHA_PRIVATE_KEY", "your-recaptcha-secret-key")

    # OAuth (optional)
    GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "your-google-client-id")
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "your-google-client-secret")

    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your-twilio-sid")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your-twilio-token")
    TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID", "your-verify-service-id")

    # Toggle OAuth (optional)
    ENABLE_SOCIAL_LOGINS = False
