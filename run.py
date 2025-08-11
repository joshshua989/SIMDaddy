
#run.py

import requests
from bs4 import BeautifulSoup
import csv
import re

player_urls = [
    # Arizona Cardinals
    "https://www.playerprofiler.com/nfl/marvin-harrison-2/",
    "https://www.playerprofiler.com/nfl/michael-wilson/",
    "https://www.playerprofiler.com/nfl/greg-dortch/",
    "https://www.playerprofiler.com/nfl/zay-jones/",

    # Atlanta Falcons
    "https://www.playerprofiler.com/nfl/drake-london/",
    "https://www.playerprofiler.com/nfl/darnell-mooney/",
    "https://www.playerprofiler.com/nfl/ray-ray-mccloud/",
    "https://www.playerprofiler.com/nfl/khadarel-hodge/",

    # Baltimore Ravens
    "https://www.playerprofiler.com/nfl/zay-flowers/",
    "https://www.playerprofiler.com/nfl/rashod-bateman/",
    "https://www.playerprofiler.com/nfl/deandre-hopkins/",
    "https://www.playerprofiler.com/nfl/devontez-walker/",
    "https://www.playerprofiler.com/nfl/tylan-wallace/",

    # Buffalo Bills
    "https://www.playerprofiler.com/nfl/khalil-shakir/",
    "https://www.playerprofiler.com/nfl/keon-coleman/",
    "https://www.playerprofiler.com/nfl/josh-palmer/",
    "https://www.playerprofiler.com/nfl/curtis-samuel/",

    # Carolina Panthers
    "https://www.playerprofiler.com/nfl/tetairoa-mcmillan/", # 2025 rookie
    "https://www.playerprofiler.com/nfl/adam-thielen/",
    "https://www.playerprofiler.com/nfl/xavier-legette/",
    "https://www.playerprofiler.com/nfl/jalen-coker/",
    "https://www.playerprofiler.com/nfl/hunter-renfrow/",

    # Chicago Bears
    "https://www.playerprofiler.com/nfl/dj-moore/",
    "https://www.playerprofiler.com/nfl/rome-odunze/",
    "https://www.playerprofiler.com/nfl/luther-burden/", # 2025 rookie
    "https://www.playerprofiler.com/nfl/olamide-zaccheaus-2/",
    "https://www.playerprofiler.com/nfl/devin-duvernay/",

    # Cincinnati Bengals
    "https://www.playerprofiler.com/nfl/jamarr-chase/",
    "https://www.playerprofiler.com/nfl/tee-higgins/",
    "https://www.playerprofiler.com/nfl/andrei-iosivas/",
    "https://www.playerprofiler.com/nfl/jermaine-burton/",
    "https://www.playerprofiler.com/nfl/charlie-jones/",

    # Cleveland Browns
    "https://www.playerprofiler.com/nfl/jerry-jeudy/",
    "https://www.playerprofiler.com/nfl/cedric-tillman/",
    "https://www.playerprofiler.com/nfl/diontae-johnson/",
    "https://www.playerprofiler.com/nfl/david-bell/",

    # Dallas Cowboys
    "https://www.playerprofiler.com/nfl/ceedee-lamb/",
    "https://www.playerprofiler.com/nfl/george-pickens/",
    "https://www.playerprofiler.com/nfl/jalen-tolbert/",
    "https://www.playerprofiler.com/nfl/kavontae-turpin/",
    "https://www.playerprofiler.com/nfl/jonathan-mingo/",

    # Denver Broncos
    "https://www.playerprofiler.com/nfl/courtland-sutton/",
    "https://www.playerprofiler.com/nfl/marvin-mims/",
    "https://www.playerprofiler.com/nfl/devaughn-vele/",
    "https://www.playerprofiler.com/nfl/troy-franklin/",
    "https://www.playerprofiler.com/nfl/pat-bryant/",

    # Detroit Lions
    "https://www.playerprofiler.com/nfl/amon-ra-st-brown/",
    "https://www.playerprofiler.com/nfl/jameson-williams/",
    "https://www.playerprofiler.com/nfl/tim-patrick/",
    "https://www.playerprofiler.com/nfl/kalif-raymond/",
    "https://www.playerprofiler.com/nfl/isaac-teslaa/",

    # Green Bay Packers
    "https://www.playerprofiler.com/nfl/jayden-reed/",
    "https://www.playerprofiler.com/nfl/matthew-golden/",
    "https://www.playerprofiler.com/nfl/romeo-doubs/",
    "https://www.playerprofiler.com/nfl/christian-watson/",
    "https://www.playerprofiler.com/nfl/dontayvion-wicks/",

    # Houston Texans
    "https://www.playerprofiler.com/nfl/nico-collins/",
    "https://www.playerprofiler.com/nfl/christian-kirk/",
    "https://www.playerprofiler.com/nfl/nathaniel-dell/",
    "https://www.playerprofiler.com/nfl/jayden-higgins/",
    "https://www.playerprofiler.com/nfl/jaylin-noel/",

    # Indianapolis Colts
    "https://www.playerprofiler.com/nfl/michael-pittman/",
    "https://www.playerprofiler.com/nfl/alec-pierce/",
    "https://www.playerprofiler.com/nfl/josh-downs/",
    "https://www.playerprofiler.com/nfl/adonai-mitchell/",
    "https://www.playerprofiler.com/nfl/ashton-dulin/",

    # Jacksonville Jaguars
    "https://www.playerprofiler.com/nfl/brian-thomas/",
    "https://www.playerprofiler.com/nfl/travis-hunter/",
    "https://www.playerprofiler.com/nfl/dyami-brown/",
    "https://www.playerprofiler.com/nfl/parker-washington/",

    # Kansas City Chiefs
    "https://www.playerprofiler.com/nfl/rashee-rice/",
    "https://www.playerprofiler.com/nfl/xavier-worthy/",
    "https://www.playerprofiler.com/nfl/marquise-brown/",
    "https://www.playerprofiler.com/nfl/juju-smith-schuster/",
    "https://www.playerprofiler.com/nfl/jalen-royals/",
    "https://www.playerprofiler.com/nfl/skyy-moore/",

    # Las Vegas Raiders
    "https://www.playerprofiler.com/nfl/jakobi-meyers/",
    "https://www.playerprofiler.com/nfl/tre-tucker/",
    "https://www.playerprofiler.com/nfl/donte-thornton/",
    "https://www.playerprofiler.com/nfl/jack-bech/",

    # Los Angeles Chargers
    "https://www.playerprofiler.com/nfl/ladd-mcconkey/",
    "https://www.playerprofiler.com/nfl/quentin-johnston/",
    "https://www.playerprofiler.com/nfl/tre-harris/", # 2025 draft pick
    "https://www.playerprofiler.com/nfl/omarion-hampton/", # 2025 draft pick
    "https://www.playerprofiler.com/nfl/derius-davis/",

    # Miami Dolphins
    "https://www.playerprofiler.com/nfl/tyreek-hill/",
    "https://www.playerprofiler.com/nfl/jaylen-waddle/",
    "https://www.playerprofiler.com/nfl/nick-westbrook/",
    "https://www.playerprofiler.com/nfl/malik-washington/",
    "https://www.playerprofiler.com/nfl/dwayne-eskridge/",
    "https://www.playerprofiler.com/nfl/erik-ezukanma/",

    # Minnesota Vikings
    "https://www.playerprofiler.com/nfl/justin-jefferson/",
    "https://www.playerprofiler.com/nfl/jordan-addison/",
    "https://www.playerprofiler.com/nfl/jalen-nailor/",
    "https://www.playerprofiler.com/nfl/tai-felton/", # 2025 draft pick

    # New Englands Patriots
    "https://www.playerprofiler.com/nfl/stefon-diggs/",
    "https://www.playerprofiler.com/nfl/demario-douglas/",
    "https://www.playerprofiler.com/nfl/mack-hollins/",
    "https://www.playerprofiler.com/nfl/kyle-williams-3/", # 2025 draft pick

    # New Orleans Saints
    "https://www.playerprofiler.com/nfl/chris-olave/",
    "https://www.playerprofiler.com/nfl/rashid-shaheed/",
    "https://www.playerprofiler.com/nfl/brandin-cooks/",
    "https://www.playerprofiler.com/nfl/bub-means/", # 2025 draft pick

    # Los Angeles Rams
    "https://www.playerprofiler.com/nfl/puka-nacua/",
    "https://www.playerprofiler.com/nfl/davante-adams/",
    "https://www.playerprofiler.com/nfl/tutu-atwell/",
    "https://www.playerprofiler.com/nfl/jordan-whittington/",

    # New York Giants
    "https://www.playerprofiler.com/nfl/malik-nabers/",
    "https://www.playerprofiler.com/nfl/wandale-robinson/",
    "https://www.playerprofiler.com/nfl/darius-slayton/",
    "https://www.playerprofiler.com/nfl/jalin-hyatt/",
    "https://www.playerprofiler.com/nfl/liljordan-humphrey/",

    # New York Jets
    "https://www.playerprofiler.com/nfl/garrett-wilson/",
    "https://www.playerprofiler.com/nfl/josh-reynolds/",
    "https://www.playerprofiler.com/nfl/allen-lazard/",
    "https://www.playerprofiler.com/nfl/malachi-corley/",

    # Philadelphia Eagles
    "https://www.playerprofiler.com/nfl/aj-brown/",
    "https://www.playerprofiler.com/nfl/devonta-smith/",
    "https://www.playerprofiler.com/nfl/jahan-dotson/",
    "https://www.playerprofiler.com/nfl/johnny-wilson/",
    "https://www.playerprofiler.com/nfl/terrace-marshall/"
    
    # Pittsburgh Steelers
    "https://www.playerprofiler.com/nfl/dk-metcalf/",
    "https://www.playerprofiler.com/nfl/calvin-austin/",
    "https://www.playerprofiler.com/nfl/robert-woods/"
    "https://www.playerprofiler.com/nfl/roman-wilson/",

    # San Francisco 49ers
    "https://www.playerprofiler.com/nfl/brandon-aiyuk/",
    "https://www.playerprofiler.com/nfl/jauan-jennings/",
    "https://www.playerprofiler.com/nfl/ricky-pearsall/",
    "https://www.playerprofiler.com/nfl/demarcus-robinson/",
    "https://www.playerprofiler.com/nfl/jacob-cowing/"
    "https://www.playerprofiler.com/nfl/jordan-watkins/"

    # Seattle Seahawks
    "https://www.playerprofiler.com/nfl/jaxon-smith-njigba/",
    "https://www.playerprofiler.com/nfl/cooper-kupp/",
    "https://www.playerprofiler.com/nfl/marquez-valdes-scantling/",
    "https://www.playerprofiler.com/nfl/tory-horton/",
    "https://www.playerprofiler.com/nfl/jake-bobo/"
    
    # Tampa Bay Buccaneers
    "https://www.playerprofiler.com/nfl/mike-evans/",
    "https://www.playerprofiler.com/nfl/chris-godwin/",
    "https://www.playerprofiler.com/nfl/emeka-egbuka/",
    "https://www.playerprofiler.com/nfl/jalen-mcmillan/",
    "https://www.playerprofiler.com/nfl/trey-palmer/",
    "https://www.playerprofiler.com/nfl/sterling-shepard/",

    # Tennessee Titans
    "https://www.playerprofiler.com/nfl/calvin-ridley/",
    "https://www.playerprofiler.com/nfl/tyler-lockett/",
    "https://www.playerprofiler.com/nfl/van-jefferson/",
    "https://www.playerprofiler.com/nfl/chimere-dike/",
    "https://www.playerprofiler.com/nfl/elic-ayomanor/",

    # Washington Commanders
    "https://www.playerprofiler.com/nfl/terry-mclaurin/",
    "https://www.playerprofiler.com/nfl/deebo-samuel/",
    "https://www.playerprofiler.com/nfl/noah-brown/",
    "https://www.playerprofiler.com/nfl/luke-mccaffrey/",
    "https://www.playerprofiler.com/nfl/jaylin-lane/",


    "https://www.playerprofiler.com/nfl/jalen-guyton/",
    "https://www.playerprofiler.com/nfl/keenan-allen/",
    "https://www.playerprofiler.com/nfl/amari-cooper/",
    "https://www.playerprofiler.com/nfl/odell-beckham/",
    "https://www.playerprofiler.com/nfl/chris-moore/",
    "https://www.playerprofiler.com/nfl/tyler-boyd/",
    "https://www.playerprofiler.com/nfl/treylon-burks/",
    "https://www.playerprofiler.com/nfl/rakim-jarrett/",
    "https://www.playerprofiler.com/nfl/laviska-shenault/",
    "https://www.playerprofiler.com/nfl/john-ross/",
    "https://www.playerprofiler.com/nfl/parris-campbell/",
    "https://www.playerprofiler.com/nfl/xavier-gipson/",
    "https://www.playerprofiler.com/nfl/mike-williams/",
    "https://www.playerprofiler.com/nfl/isaiah-hodgins/",
    "https://www.playerprofiler.com/nfl/justin-shorter/",
    "https://www.playerprofiler.com/nfl/cedrick-wilson/",
    "https://www.playerprofiler.com/nfl/nelson-agholor/",
    "https://www.playerprofiler.com/nfl/brandon-powell/",
    "https://www.playerprofiler.com/nfl/brenden-rice/",
    "https://www.playerprofiler.com/nfl/justin-watson/",
    "https://www.playerprofiler.com/nfl/bo-melton/",
    "https://www.playerprofiler.com/nfl/antoine-green/",
    "https://www.playerprofiler.com/nfl/elijah-moore/",
    "https://www.playerprofiler.com/nfl/tyler-scott/",
]


# Map full team names to abbreviations for current teams
TEAM_ABBREV = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Buffalo Bills": "BUF",
    "Baltimore Ravens": "BAL",
    "Carolina Panthers": "CAR",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}

COLUMNS = [
    "Year", "Team", "Player", "Position", "Height", "Weight", "ArmLength", "ArmLengthRank", "DraftPick", "DraftYear", "College",
    "Targets", "TargetShare", "RzTargetShare", "TargetRate", "SnapShare", "SlotSnaps", "SlotSnapRate", "RoutesRun", "RouteParticipation", "AirYards", "AirYardsShare",
    "AvgTargetDistADOT", "DeepTargets", "RzTargets", "RzRec", "TargetQualityRating", "CatchableTargetRate", "CatchableTargets", "TargetAccuracy", "YardsPerRouteRun", "FormationAdjustedYardsPerRouteRun",
    "YardsPerTarget", "YardsPerRec", "YardsPerTeamPassAtt", "TrueCatchRate", "TargetSeparation", "TargetPrem", "DominatorRating", "JukeRate", "ExplosiveRating", "Drops",
    "DropRate", "ContestedCatchRate", "ContestedCatchTargets", "ProductionPrem", "ExpectedPointsAddedEPA", "QbRatingPerTarget", "BestBallPointsAdded", "FantasyPointsPerRouteRun", "FantasyPointsPerTarget", "TotalFantasyPoints",
    "TotalRouteWins", "RouteWinRate", "RoutesVsMan", "RoutesVsZone", "WinRateVsMan", "WinRateVsZone", "TargetRateVsMan", "TargetRateVsZone", "TargetSeparationVsMan",
    "TargetSeparationVsZone", "FantasyPointsPerTargetVsMan", "FantasyPointsPerTargetVsZone"
]

def clean_number(val):
    val = val.replace(",", "")
    try:
        return str(float(val))
    except:
        return val


import re

def height_to_inches(height_str):
    """Convert height like 6' 3" or 6′3″ into inches."""
    if not height_str:
        return ""
    # Normalize quotes and remove spaces
    height_str = (
        height_str.replace("’", "'")
                  .replace("‘", "'")
                  .replace("″", '"')
                  .replace("“", '"')
                  .replace("”", '"')
                  .replace(" ", "")  # Remove space between feet and inches
    )
    match = re.match(r"(\d+)'(\d+)", height_str)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2))
        return feet * 12 + inches
    return ""

def get_profile_stats(soup):
    profile = {}

    # Player name
    name = soup.select_one("h1.font-display")
    profile["Player"] = name.get_text(strip=True) if name else ""

    # Team
    team_div = soup.select_one(".player-page__header-team .font-display")
    team = team_div.get_text(strip=True) if team_div else ""
    profile["Team"] = TEAM_ABBREV.get(team, team[:3].upper())

    # Position (e.g., WR61)
    pos_div = soup.select_one(".player-page__header-pos .text-lg")
    profile["Position"] = pos_div.get_text(strip=True) if pos_div else ""

    # Core stats
    stat_divs = soup.select(".player-page__core-stat")
    for div in stat_divs:
        label = div.select_one(".text-blue-light")
        value = div.select_one(".font-display")
        if not label or not value:
            continue
        text = label.text.strip().lower()
        val = value.text.strip()

        if "height" in text:
            profile["Height"] = val  # e.g., 6'1"
            profile["HeightInches"] = height_to_inches(val) or ""

        elif "weight" in text:
            profile["Weight"] = re.sub(r"[^\d]", "", val)

        elif "arm length" in text:
            profile["ArmLength"] = re.sub(r"[^\d.]", "", val)
            rank_span = div.select_one("span.text-xs")
            if rank_span:
                profile["ArmLengthRank"] = re.sub(r"[^\d]", "", rank_span.text)

        elif "draft pick" in text:
            profile["DraftPick"] = "Undrafted" if "undrafted" in val.lower() else val
            year_match = re.search(r"\((\d{4})\)", div.text)
            if year_match:
                profile["DraftYear"] = year_match.group(1)

        elif "college" in text:
            profile["College"] = val

    # Fill in blanks for any missing keys
    for k in ["Height", "HeightInches", "Weight", "ArmLength", "ArmLengthRank", "DraftPick", "DraftYear", "College"]:
        if k not in profile:
            profile[k] = ""

    return profile


def scrape_player(url):
    print("Scraping", url)
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    out = {}
    out["Year"] = "2024"

    # Profile stats
    profile = get_profile_stats(soup)
    out.update(profile)

    # Fill any remaining columns with blanks
    for col in COLUMNS:
        if col not in out:
            out[col] = ""

    return [out[col] for col in COLUMNS]


# Write CSV
with open("DATA/player_profiler_data/WR_STATS_2024_test.csv", "w", newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(COLUMNS)
    for url in player_urls:
        row = scrape_player(url)
        print(row)
        writer.writerow(row)
    print("Done! Saved to DATA/player_profiler_data/WR_STATS_2024_test_.csv")
