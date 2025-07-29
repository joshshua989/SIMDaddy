import requests
import pandas as pd
import re
import time

ODDS_API_KEY = "82db1e191bc4c97af4330406ea8b34e9"
BOOKMAKER = "draftkings"
SPORT = "americanfootball_nfl"
REGION = "us"
MARKETS = "player_receiving_yards,player_receptions,player_touchdowns"

# Standardize names to match roster_2025.csv
name_cleaner = lambda x: re.sub(r'[^a-z]', '', x.lower().split(" ")[0] + x.lower().split(" ")[-1])

def fetch_wr_props():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "regions": REGION,
        "markets": MARKETS,
        "apiKey": ODDS_API_KEY,
        "bookmakers": BOOKMAKER
    }

    print("Fetching odds from OddsAPI...")
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code} - {response.text}")

    all_data = response.json()
    props = []

    for game in all_data:
        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    clean_name = name_cleaner(name)
                    props.append({
                        "player": name,
                        "player_clean": clean_name,
                        "market": market_key,
                        "value": outcome.get("point"),
                        "matchup": f"{game.get('home_team')} vs {game.get('away_team')}",
                        "game_time": game.get("commence_time")
                    })

    df = pd.DataFrame(props)
    if df.empty:
        print("No WR props found.")
        return

    df = df[df["market"].isin(["player_receiving_yards", "player_receptions", "player_touchdowns"])]
    df.to_csv("wr_prop_market.csv", index=False)
    print("Saved to wr_prop_market.csv")

if __name__ == "__main__":
    fetch_wr_props()
