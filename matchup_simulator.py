
# matchup_simulator.py

import pandas as pd
import numpy as np
from collections import defaultdict

from config import (
    PROJECTION_WEIGHTS,
    DEFAULT_MAN_ZONE_BLEND,
    BLENDED_DB_FILE,
    BLENDED_WR_FILE,
    USE_SOFT_ALIGNMENT,
    USE_GAME_SCRIPT_BOOST,
    USE_ADVANCED_GAME_SCRIPT_MODEL,
    ENABLE_GAME_SCRIPT_EXPLANATION,
    ROLE_MULTIPLIER
)

# --- Classes ---
class DB:
    def __init__(self, name, team, position):
        self.name = name
        self.team = team
        self.position = position
        self.coverage_stats = {}
        self.alignment_role = None
        self.alignment_probs = {}

    def load_alignment_profile(self, row):
        self.coverage_stats = {
            "targets_allowed": row.get("Targets Allowed", 0),
            "catch_rate": row.get("Catch Rate Allowed", 0),
            "passer_rating": row.get("Passer Rating Allowed", 0),
            "fpts_per_target": row.get("Fantasy Points Allowed Per Target", 0),
            "fpts_per_game": row.get("Fantasy Points Allowed Per Game", 0),
            "man_success": row.get("Man Coverage Success Rate", 0),
            "separation": row.get("Target Separation", 0)
        }

        # Hard role assignment
        if self.position == 'S':
            # If the player's position is a Safety ('S'), they're automatically labeled as "safety", regardless of coverage stats.
            self.alignment_role = "safety"
        elif self.position == 'LB':
            self.alignment_role = "linebacker"
        elif row.get("Man Coverage Rate", 0) > 0.5:
            # If the DB is not a safety and their man coverage rate is over 50%, we assume they often play outside (wide) where man coverage is more common.
            self.alignment_role = "wide"
        elif row.get("Catch Rate Allowed", 0) > 0.7:
            # If their catch rate allowed is greater than 70%, it's assumed they're likely a slot corner (since slot defenders often face quick, high-efficiency routes that lead to high catch rates).
            self.alignment_role = "slot"
        else:
            # Default case: if none of the above conditions apply, assign them as "wide" (outside CB).
            self.alignment_role = "wide"

        # Soft alignment probabilities
        slot_score = row.get("Catch Rate Allowed", 0)
        wide_score = row.get("Man Coverage Rate", 0)
        safety_score = 1.0 if self.position == 'S' else 0.0
        lb_score = 1.0 if self.position == 'LB' else 0.0

        raw = np.array([slot_score, wide_score, safety_score, lb_score])
        probs = raw / raw.sum() if raw.sum() > 0 else np.array([0.25, 0.25, 0.25, 0.25])
        self.alignment_probs = dict(zip(["slot", "wide", "safety", "linebacker"], probs))


class WR:
    def __init__(self, name, position, team):
        self.name = name
        self.position = position
        self.team = team
        self.role = None
        self.slot_snap_rate = 0.0
        self.wide_snap_rate = 0.0
        self.snap_share = 0.0
        self.routes_run = 0
        self.is_slot = False
        self.alignment_weights = {}
        self.weekly_stats = {}
        self.vs_man = {}
        self.vs_zone = {}

    def load_alignment_and_coverage(self, row):
        self.slot_snap_rate = row.get("SlotSnapRate", 0)
        self.snap_share = row.get("SnapShare", 0)
        self.routes_run = row.get("RoutesRun", 0)
        self.wide_snap_rate = 1.0 - self.slot_snap_rate
        self.alignment_weights = {
            "slot": self.slot_snap_rate * PROJECTION_WEIGHTS["slot"],
            "wide": self.wide_snap_rate * PROJECTION_WEIGHTS["wide"],
            "safety": (0.2 if self.slot_snap_rate > 0.3 else 0.05) * PROJECTION_WEIGHTS["safety"],
            "lb": (0.1 if self.slot_snap_rate > 0.2 else 0.0) * PROJECTION_WEIGHTS["lb"]
        }
        self.vs_man = {
            "routes": row.get("RoutesVsMan", 0),
            "win_rate": row.get("WinRateVsMan", 0),
            "target_rate": row.get("TargetRateVsMan", 0),
            "separation": row.get("TargetSeparationVsMan", 0),
            "fpts_per_target": row.get("FantasyPointsPerTargetVsMan", 0)
        }
        self.vs_zone = {
            "routes": row.get("RoutesVsZone", 0),
            "win_rate": row.get("WinRateVsZone", 0),
            "target_rate": row.get("TargetRateVsZone", 0),
            "separation": row.get("TargetSeparationVsZone", 0),
            "fpts_per_target": row.get("FantasyPointsPerTargetVsZone", 0)
        }

# --- Loaders ---
def load_db_alignment(filepath=BLENDED_DB_FILE):
    df = pd.read_csv(filepath)
    db_map = defaultdict(dict)
    sample_printed = False

    for _, row in df.iterrows():
        name = row.get('PlayerYear', row.get('Player', 'Unknown Player'))
        team = row['Team']
        pos = row['Position']
        db = DB(name, team, pos)
        db.load_alignment_profile(row)
        db_map[team][name] = db

        # Print first sample row
        if not sample_printed:
            print(f"\n(SAMPLE) {filepath}:")
            print(f"🔍 DB Name: {db.name}")
            print(f"🏈 Team: {db.team}")
            print(f"📌 Position: {db.position}")
            print(f"🎯 Role: {db.alignment_role}")
            print("📊 Coverage Stats:")
            for k, v in db.coverage_stats.items():
                print(f"   - {k}: {v}")
            sample_printed = True

    return db_map

def load_wr_stats(filepath=BLENDED_WR_FILE):
    df = pd.read_csv(filepath)
    wrs = {}
    sample_printed = False

    for _, row in df.iterrows():
        name = row['Player']
        team = row['Team']
        wr = WR(name, 'WR', team)
        wr.load_alignment_and_coverage(row)
        wrs[name] = wr

        # Print first sample row
        if not sample_printed:
            print(f'\n(SAMPLE) {filepath}:')
            print(f"🔍 WR Name: {wr.name}")
            print(f"🏈 Team: {wr.team}")
            print(f"📌 Position: {wr.position}")
            print(f"📊 Slot Snap Rate: {wr.slot_snap_rate}")

            print("\n🛡️ vs Man Coverage:")
            for k, v in wr.vs_man.items():
                print(f"  - {k}: {v}")

            print("\n🛡️ vs Zone Coverage:")
            for k, v in wr.vs_zone.items():
                print(f"  - {k}: {v}")
            sample_printed = True

    print("")
    print(wrs.keys())

    return wrs

# --- Logic ---
def role_based_penalty(stats, role):
    if role == "slot":
        return (stats["catch_rate"] + stats["fpts_per_target"]) / 2
    elif role == "wide":
        return (stats["separation"] + stats["passer_rating"]) / 2 / 100
    elif role == "safety":
        return stats["catch_rate"] * 0.7 + stats["separation"] * 0.3
    elif role == "linebacker":
        return stats["fpts_per_game"] / 15.0
    return 1.0

def db_penalty_profile(week, team, db_map, coverage_map):
    scheme = coverage_map.get(week, {}).get(team, "man")
    db_pool = db_map.get(team, {})
    penalties = {"slot": [], "wide": [], "safety": [], "linebacker": []}
    for db in db_pool.values():
        penalties[db.alignment_role].append(role_based_penalty(db.coverage_stats, db.alignment_role))
    return {
        "slot_penalty": np.mean(penalties["slot"]) if penalties["slot"] else 1.0,
        "wide_penalty": np.mean(penalties["wide"]) if penalties["wide"] else 1.0,
        "safety_penalty": np.mean(penalties["safety"]) if penalties["safety"] else 1.0,
        "lb_penalty": np.mean(penalties["linebacker"]) if penalties["linebacker"] else 1.0,
        "scheme": scheme
    }

def recent_form_boost(wr, week):
    recent = [wr.weekly_stats[w]['adj_pts'] for w in range(week - 3, week) if w in wr.weekly_stats]
    return 1 + (np.mean(recent) - 10) / 30 if recent else 1.0

# -------------------------------
# CALCULATE_SCRIPT_BOOST
# -------------------------------

def calculate_script_boost(
    wr, matchup_row, multipliers, week=None, explain=False
):
    """
    Estimate the impact of game script (score differential, team/WR tendencies, QB, etc) on WR projection.

    Args:
        wr: WR object (should have .team, .name, .role, optionally .qb_name)
        matchup_row: pd.Series or dict with keys like 'Team', 'Opponent', 'ProjectedHomeScore', 'ProjectedAwayScore'
        multipliers: dict of all loaded multiplier dicts (from CSVs)
        explain: if True, returns (boost, explanation)

    Returns:
        float or (float, explanation)
    """

    if multipliers is None:
        raise ValueError("Multipliers dict is None! (Check pool args)")

    # --- Parse home/away and projected scores ---
    home_team = matchup_row['Team']
    away_team = matchup_row['Opponent']
    is_home_wr = (wr.team == home_team)
    try:
        ph = float(matchup_row.get("ProjectedHomeScore", 0))
        pa = float(matchup_row.get("ProjectedAwayScore", 0))
    except Exception as e:
        if explain:
            return 0.0, f"Missing projected points: {e}"
        return 0.0

    # --- Calculate score differential (from WR's team perspective) ---
    # --- (positive = trailing, negative = leading) ---
    proj_diff = (pa - ph) if is_home_wr else (ph - pa)

    # --- Legacy flat boost ---
    if not USE_ADVANCED_GAME_SCRIPT_MODEL:
        # Legacy flat boost logic
        if proj_diff > 7:
            if explain: return 0.10, "Legacy: >7 underdog = +10%"
            return 0.10
        elif proj_diff < -7:
            if explain: return -0.05, "Legacy: <-7 big favorite = -5%"
            return -0.05
        else:
            if explain: return 0.0, "Legacy: neutral"
            return 0.0

    # --- Advanced base gradient logic ---

    # --- Each point of projected point differential gives a 1.5% adjustment ---
    # --- Result is capped between -7% and +12% ---
    base_boost = min(max(proj_diff * 0.015, -0.07), 0.12)  # -7% to +12%

    # --- Multipliers ---

    team_mult = float(multipliers.get("team_script_response", {}).get(wr.team, 1.0))
    pace_mult = float(multipliers.get("pace_multiplier", {}).get(wr.team, 1.0))
    competition_mult = float(multipliers.get("wr_target_competition", {}).get(wr.name, 1.0))
    wr_mult = float(multipliers.get("wr_script_sensitivity", {}).get(wr.name, 1.0))
    role = getattr(wr, "role", "WR1")
    role_mult = float(ROLE_MULTIPLIER.get(role, 1.0))
    air_mult = float(multipliers.get("wr_air_yards_share", {}).get(wr.name, 1.0))
    injury_mult = float(multipliers.get("wr_injury_status", {}).get(wr.name, 1.0))
    qb_name = wr.qb if hasattr(wr, 'qb') else None  # set in WR or elsewhere
    qb_mult = float(multipliers.get("qb_script_response", {}).get(qb_name, 1.0))
    qb_agg = float(multipliers.get("qb_aggressiveness", {}).get(qb_name, 1.0))
    def_mult = float(multipliers.get("def_pass_rate_allowed", {}).get(away_team, 1.0))
    pressure_mult = float(multipliers.get("def_pressure_rate_allowed", {}).get(away_team, 1.0))

    # --- Final Calculation (all factors included) ---
    final_boost = round(
        base_boost
        * team_mult
        * wr_mult
        * qb_mult
        * qb_agg
        * pace_mult
        * def_mult
        * pressure_mult
        * role_mult
        * air_mult
        * competition_mult
        * injury_mult,
        4
    )

    if explain:
        explanation = (
            f"BaseBoost={base_boost:.3f}, "
            f"TeamMult={team_mult}, WRMult={wr_mult}, QBMult={qb_mult}, QB_Agg={qb_agg}, "
            f"PaceMult={pace_mult}, DefMult={def_mult}, PressureMult={pressure_mult}, "
            f"RoleMult={role_mult}, AirMult={air_mult}, CompetitionMult={competition_mult}, "
            f"InjuryMult={injury_mult} => FinalBoost={final_boost}"
        )
        return final_boost, explanation

    return final_boost

# -------------------------------
# PROJECT_WR_WEEK
# -------------------------------

#Defines the core function to simulate a WR’s fantasy projection for a single week.
def project_wr_week(
    wr, week, schedule_df, db_alignment_map, coverage_map, 
    simulations=0, std_dev=2.0, precomputed=None, env_boost_map=None,
    multipliers=None
):
    #Logs the WR and week for debugging.
    print(f"project_wr_week: {wr.name} (Team: {wr.team}), Week: {week}")

    if multipliers is None:
        raise ValueError("Multipliers dict is None! (Check pool args)")

    #Looks up the WR’s matchup row for this week. If not found, returns None.
    matchup_row = schedule_df[
        (schedule_df['Week'] == week) &
        ((schedule_df['Team'] == wr.team) | (schedule_df['Opponent'] == wr.team))
        ]
    print(f"  - matchup_row found: {len(matchup_row)}")
    if matchup_row.empty:
        print(f"  - No matchup found for {wr.name} in week {week}")
        return None
    row = matchup_row.iloc[0]

    #Calculate script boost (with/without explanation), storing values for later use
    script_boost, script_explanation = 0.0, None
    if USE_GAME_SCRIPT_BOOST:
        if ENABLE_GAME_SCRIPT_EXPLANATION:
            script_boost, script_explanation = calculate_script_boost(wr, row, multipliers, week=week, explain=True)
            print(script_explanation)
        else:
            script_boost = calculate_script_boost(wr, row, multipliers, week=week)

    #Identifies opponent team and defensive scheme type (man/zone).
    opp_team = row['Opponent'] if row['Team'] == wr.team else row['Team']
    scheme = coverage_map.get(week, {}).get(opp_team, "man" if DEFAULT_MAN_ZONE_BLEND else "unknown")

    #Fetches the WR’s alignment weights (slot, wide, etc).
    weights = wr.alignment_weights
    total_weight = sum(weights.values())

    #Sets base points per target based on scheme. Gets the pool of DBs for the opponent team.
    base_pts = wr.vs_man['fpts_per_target'] if scheme == 'man' else wr.vs_zone['fpts_per_target']
    db_pool = db_alignment_map.get(opp_team, {})

    if precomputed:
        penalties = {
            "slot": precomputed.get("slot_penalty", 1.0),
            "wide": precomputed.get("wide_penalty", 1.0),
            "safety": precomputed.get("safety_penalty", 1.0),
            "lb": precomputed.get("lb_penalty", 1.0)
        }
    elif USE_SOFT_ALIGNMENT:
        penalties = {"slot": [], "wide": [], "safety": [], "linebacker": []}
        for db in db_pool.values():
            for role, prob in db.alignment_probs.items():
                penalty = role_based_penalty(db.coverage_stats, role)
                penalties[role].append(prob * penalty)

        # Ensure all roles exist in the penalties dictionary
        penalties = {r: penalties.get(r, []) for r in ['slot', 'wide', 'safety', 'lb']}

        # Compute safe averages or use 1.0 fallback
        penalties = {
            r: (np.sum(penalties[r]) / len(penalties[r])) if penalties[r] else 1.0
            for r in penalties
        }

    else:
        penalties = {}
        for role in weights:
            dbs = [db for db in db_pool.values() if db.alignment_role == role]
            penalties[role] = np.mean([role_based_penalty(db.coverage_stats, role) for db in dbs]) if dbs else 1.0

    adjusted_pts = base_pts * sum(weights[r] * (1 - penalties[r]) for r in weights) / total_weight
    adjusted_pts *= recent_form_boost(wr, week)

    # --- Environment Boost ---
    env_boost = 1.0
    deep_penalty, short_penalty = 1.0, 1.0
    if env_boost_map and week in env_boost_map and opp_team in env_boost_map[week]:
        env_info = env_boost_map[week][opp_team]
        if isinstance(env_info, dict):
            env_boost = env_info.get("boost", 1.0)
            deep_penalty = env_info.get("deep_penalty", 1.0)
            short_penalty = env_info.get("short_penalty", 1.0)
        elif isinstance(env_info, (float, int)):
            env_boost = env_info

    # -- APPLY ENVIRONMENT BOOSTS --
    adjusted_pts *= env_boost
    adjusted_pts *= (1 + script_boost)

    # --- APPLY ROUTE-TYPE WEATHER PENALTIES ---
    if multipliers is not None:
        air_share = multipliers.get("wr_air_yards_share", {}).get(wr.name, 0.4)
        route_weather_mult = (air_share * deep_penalty) + ((1 - air_share) * short_penalty)
        adjusted_pts *= route_weather_mult
    else:
        route_weather_mult = 1.0

    result = {
        'week': week,
        'wr_name': wr.name,
        'team': wr.team,
        'opp_team': opp_team,
        'scheme': scheme,
        'base_pts': round(base_pts, 2),
        'adj_pts': round(adjusted_pts, 2),
        'slot_weight': round(weights['slot'], 2),
        'wide_weight': round(weights['wide'], 2),
        'safety_weight': round(weights['safety'], 2),
        'lb_weight': round(weights['lb'], 2),
        'env_boost': round(env_boost, 3),
        'game_script_boost': round(script_boost, 3),
        'route_weather_mult': round(route_weather_mult, 3),
        'final_pts': round(adjusted_pts, 2)
    }
    if ENABLE_GAME_SCRIPT_EXPLANATION and script_explanation is not None:
        result['game_script_explanation'] = script_explanation

    if simulations > 0:
        samples = np.random.normal(loc=adjusted_pts, scale=std_dev, size=simulations)
        result['adj_pts_p25'] = round(np.percentile(samples, 25), 2)
        result['adj_pts_p50'] = round(np.percentile(samples, 50), 2)
        result['adj_pts_p75'] = round(np.percentile(samples, 75), 2)

    wr.weekly_stats[week] = result
    return result
