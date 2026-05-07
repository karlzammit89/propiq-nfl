"""
PropIQ — Live Roster & Stats Engine
Replaces the static player_db.py entirely.

Pulls LIVE from ESPN every 6 hours:
  - All 32 NFL team rosters (QB/RB/WR/TE only)
  - Current team assignment (trades, signings, cuts reflected immediately)
  - Season per-game averages for each player
  - Standard deviations estimated from position/tier
  - L5 form factor from recent game logs
  - Historical hit rate priors by position

ESPN endpoints used (all free, no auth):
  Roster  : site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{id}/roster
  Stats   : sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{yr}/types/2/athletes/{id}/statistics
  Gamelog : sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{yr}/athletes/{id}/eventlog
"""

import requests
import time
import streamlit as st
from utils.fallback_data import ESPN_TEAM_IDS, FALLBACK_DEF_RATINGS

# ── Constants ─────────────────────────────────────────────────────────────────
ESPN_SITE   = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_CORE   = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
CURRENT_SEASON = 2024          # update each season start
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}

# ── Position stat priors (fallback when ESPN returns no stats) ────────────────
# Format: {stat: (mean, std_multiplier)}
POSITION_PRIORS = {
    "QB": {
        "pass_yds": 245, "pass_tds": 1.6, "rush_yds": 18, "rush_att": 3.5,
        "completions": 20.5, "attempts": 31.0,
        "anytime_td": 0.60, "first_td": 0.17,
        "rec_yds": 0, "receptions": 0, "rec_tds": 0, "longest_rec": 0,
        "_std": {"pass_yds": 62, "pass_tds": 0.92, "rush_yds": 14,
                 "completions": 4.0, "attempts": 5.0},
        "_hr": {"pass_yds": 0.59, "pass_tds": 0.55, "rush_yds": 0.50},
        "_l5": 1.00,
    },
    "RB": {
        "pass_yds": 0, "pass_tds": 0, "rush_yds": 58, "rush_att": 12.5,
        "completions": 0, "attempts": 0,
        "rec_yds": 28, "receptions": 3.2, "rec_tds": 0.10,
        "longest_rec": 14, "anytime_td": 0.55, "first_td": 0.16,
        "_std": {"rush_yds": 26, "rush_att": 2.6, "rec_yds": 14, "receptions": 1.4},
        "_hr": {"rush_yds": 0.58, "rec_yds": 0.48, "rush_att": 0.60},
        "_l5": 1.00,
    },
    "WR": {
        "pass_yds": 0, "pass_tds": 0, "rush_yds": 0, "rush_att": 0.1,
        "completions": 0, "attempts": 0,
        "rec_yds": 55, "receptions": 4.5, "rec_tds": 0.30,
        "longest_rec": 22, "anytime_td": 0.44, "first_td": 0.13,
        "_std": {"rec_yds": 24, "receptions": 1.8, "rush_yds": 0},
        "_hr": {"rec_yds": 0.58, "receptions": 0.57, "rec_tds": 0.33},
        "_l5": 1.00,
    },
    "TE": {
        "pass_yds": 0, "pass_tds": 0, "rush_yds": 0, "rush_att": 0,
        "completions": 0, "attempts": 0,
        "rec_yds": 44, "receptions": 4.0, "rec_tds": 0.26,
        "longest_rec": 18, "anytime_td": 0.36, "first_td": 0.10,
        "_std": {"rec_yds": 18, "receptions": 1.6, "rush_yds": 0},
        "_hr": {"rec_yds": 0.54, "receptions": 0.55, "rec_tds": 0.29},
        "_l5": 1.00,
    },
}

# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(url: str, params: dict = None, timeout: int = 12) -> dict | None:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── ROSTER FETCH ──────────────────────────────────────────────────────────────

def _fetch_team_roster(team_abbr: str, espn_id: int) -> list[dict]:
    """
    Pull current roster for one team from ESPN.
    Returns list of {id, name, pos, num, team, espn_id}
    """
    data = _get(f"{ESPN_SITE}/teams/{espn_id}/roster")
    if not data:
        return []

    players = []
    for group in data.get("athletes", []):
        # ESPN returns athletes grouped by position group
        for athlete in group.get("items", []):
            pos = athlete.get("position", {}).get("abbreviation", "")
            if pos not in SKILL_POSITIONS:
                continue
            players.append({
                "id":      str(athlete.get("id", "")),
                "name":    athlete.get("fullName", athlete.get("displayName", "")),
                "pos":     pos,
                "num":     athlete.get("jersey", "—"),
                "team":    team_abbr,
                "espn_id": str(athlete.get("id", "")),
            })
    return players


# ── STATS FETCH ───────────────────────────────────────────────────────────────

def _fetch_player_stats(espn_athlete_id: str, pos: str) -> dict:
    """
    Pull season stats for a player from ESPN core API.
    Returns merged stat dict ready for the engine.
    """
    url = (
        f"{ESPN_CORE}/seasons/{CURRENT_SEASON}/types/2"
        f"/athletes/{espn_athlete_id}/statistics"
    )
    data = _get(url)
    if not data:
        return {}

    try:
        splits = data.get("splits", {})
        categories = splits.get("categories", [])
        raw = {}
        for cat in categories:
            for stat in cat.get("stats", []):
                raw[stat.get("name", "")] = stat.get("value", 0)

        games = max(1, int(raw.get("gamesPlayed", 1)))

        if pos == "QB":
            return {
                "pass_yds":    _pg(raw, "passingYards", games),
                "pass_tds":    _pg(raw, "passingTouchdowns", games),
                "rush_yds":    _pg(raw, "rushingYards", games),
                "rush_att":    _pg(raw, "rushingAttempts", games),
                "completions": _pg(raw, "completions", games),
                "attempts":    _pg(raw, "passingAttempts", games),
                "rec_yds": 0, "receptions": 0, "rec_tds": 0, "longest_rec": 0,
                "anytime_td":  min(0.95, _pg(raw, "passingTouchdowns", games) * 0.38 + 0.05),
                "first_td":    min(0.40, _pg(raw, "passingTouchdowns", games) * 0.09),
                "_games": games,
            }
        elif pos == "RB":
            rec_td = _pg(raw, "receivingTouchdowns", games)
            rush_td = _pg(raw, "rushingTouchdowns", games)
            total_td = rec_td + rush_td
            return {
                "pass_yds": 0, "pass_tds": 0, "completions": 0, "attempts": 0,
                "rush_yds":    _pg(raw, "rushingYards", games),
                "rush_att":    _pg(raw, "rushingAttempts", games),
                "rec_yds":     _pg(raw, "receivingYards", games),
                "receptions":  _pg(raw, "receptions", games),
                "rec_tds":     rec_td,
                "longest_rec": _pg(raw, "longReception", games, per_game=False),
                "anytime_td":  min(0.95, total_td * 2.8),
                "first_td":    min(0.45, total_td * 0.85),
                "_games": games,
            }
        elif pos in ("WR", "TE"):
            rec_td = _pg(raw, "receivingTouchdowns", games)
            rush_yds = _pg(raw, "rushingYards", games)
            return {
                "pass_yds": 0, "pass_tds": 0, "completions": 0, "attempts": 0,
                "rush_yds":    rush_yds,
                "rush_att":    _pg(raw, "rushingAttempts", games),
                "rec_yds":     _pg(raw, "receivingYards", games),
                "receptions":  _pg(raw, "receptions", games),
                "rec_tds":     rec_td,
                "longest_rec": _pg(raw, "longReception", games, per_game=False),
                "anytime_td":  min(0.95, rec_td * 2.8),
                "first_td":    min(0.40, rec_td * 0.85),
                "_games": games,
            }
    except Exception:
        pass
    return {}


def _pg(raw: dict, key: str, games: int, per_game: bool = True) -> float:
    v = float(raw.get(key, 0))
    return round(v / games, 2) if per_game and games > 0 else round(v, 1)


# ── L5 FORM ───────────────────────────────────────────────────────────────────

def _fetch_l5_mod(espn_athlete_id: str, pos: str, season_avg: dict) -> float:
    """
    Compare last 5 games vs season average for the primary stat.
    Returns multiplier (e.g. 1.08 = 8% above average recently).
    """
    url = (
        f"{ESPN_CORE}/seasons/{CURRENT_SEASON}"
        f"/athletes/{espn_athlete_id}/eventlog"
    )
    data = _get(url)
    if not data:
        return 1.00

    try:
        events = data.get("events", {}).get("items", [])
        if not events:
            return 1.00

        # Primary stat key by position
        stat_map = {
            "QB": "passingYards",
            "RB": "rushingYards",
            "WR": "receivingYards",
            "TE": "receivingYards",
        }
        primary = stat_map.get(pos, "receivingYards")
        season_val = season_avg.get(
            "pass_yds" if pos == "QB" else
            "rush_yds" if pos == "RB" else "rec_yds", 1
        )
        if not season_val:
            return 1.00

        recent_vals = []
        for ev in reversed(events[-8:]):   # last 8 game entries
            stats_url = ev.get("$ref", "")
            if not stats_url:
                continue
            ev_data = _get(stats_url)
            if not ev_data:
                continue
            for cat in ev_data.get("splits", {}).get("categories", []):
                for s in cat.get("stats", []):
                    if s.get("name") == primary:
                        recent_vals.append(float(s.get("value", 0)))
            if len(recent_vals) >= 5:
                break

        if len(recent_vals) < 3:
            return 1.00

        l5_avg = sum(recent_vals[-5:]) / len(recent_vals[-5:])
        mod = round(l5_avg / max(1, season_val), 3)
        return max(0.60, min(1.50, mod))   # cap at ±50%

    except Exception:
        return 1.00


# ── STD & HR ESTIMATION ───────────────────────────────────────────────────────

def _estimate_std_and_hr(stats: dict, pos: str) -> tuple[dict, dict]:
    """
    Estimate per-stat standard deviation and historical hit rates
    from season averages using position-specific coefficients.
    """
    CV = {   # coefficient of variation by stat (std ≈ mean × CV)
        "pass_yds": 0.20, "pass_tds": 0.55, "rush_yds": 0.38,
        "rush_att": 0.22, "rec_yds": 0.40, "receptions": 0.35,
        "completions": 0.17, "attempts": 0.15,
    }
    std = {}
    for k, cv in CV.items():
        val = stats.get(k, 0)
        if val:
            std[k] = max(3.0, round(val * cv, 1))
        else:
            prior_std = POSITION_PRIORS.get(pos, {}).get("_std", {})
            std[k] = prior_std.get(k, 5.0)

    # Hit rates: correlated with volume — more volume = more consistent
    prior_hr = POSITION_PRIORS.get(pos, {}).get("_hr", {})
    hr = {}
    for k, base in prior_hr.items():
        vol = stats.get(k, 0)
        if vol:
            # Higher-volume players hit more consistently
            vol_boost = min(0.12, max(-0.08, (vol - 50) / 500))
            hr[k] = round(max(0.35, min(0.80, base + vol_boost)), 3)
        else:
            hr[k] = base

    return std, hr


# ── TIER ASSIGNMENT ───────────────────────────────────────────────────────────

def _assign_tier(stats: dict, pos: str) -> int:
    """Tier 1 = starter / featured, 2 = rotational, 3 = depth."""
    if pos == "QB":
        return 1  # all QBs on roster are worth showing
    if pos == "RB":
        rush = stats.get("rush_att", 0)
        return 1 if rush >= 14 else (2 if rush >= 8 else 3)
    if pos == "WR":
        rec = stats.get("receptions", 0)
        return 1 if rec >= 5.5 else (2 if rec >= 3.0 else 3)
    if pos == "TE":
        rec = stats.get("receptions", 0)
        return 1 if rec >= 4.5 else (2 if rec >= 2.5 else 3)
    return 3


# ── MAIN LIVE DB BUILDER ──────────────────────────────────────────────────────

@st.cache_data(ttl=21600, show_spinner=False)   # refresh every 6 hours
def build_live_player_db(progress_callback=None) -> dict:
    """
    Build the complete player database live from ESPN.
    Called once on app load, cached for 6 hours.
    Returns dict keyed by a stable player ID string.

    Each entry matches the structure expected by utils/engine.py:
    {
        name, team, pos, num, tier, espn_id,
        pass_yds, pass_tds, rush_yds, rush_att,
        completions, attempts, rec_yds, receptions, rec_tds,
        longest_rec, anytime_td, first_td,
        std: {…}, l5: float, hr: {…},
    }
    """
    db = {}
    total_teams = len(ESPN_TEAM_IDS)
    fetched_players = 0
    failed_teams = []

    for i, (team_abbr, espn_id) in enumerate(ESPN_TEAM_IDS.items()):
        if progress_callback:
            progress_callback(i / total_teams, f"Loading {team_abbr} roster…")

        roster = _fetch_team_roster(team_abbr, espn_id)
        if not roster:
            failed_teams.append(team_abbr)
            continue

        for player in roster:
            pid     = player["espn_id"]
            pos     = player["pos"]
            name    = player["name"]

            # Pull live stats
            live_stats = _fetch_player_stats(pid, pos)

            # Merge with position priors for any missing fields
            prior = POSITION_PRIORS.get(pos, POSITION_PRIORS["WR"])
            merged = {}
            stat_keys = [
                "pass_yds", "pass_tds", "rush_yds", "rush_att",
                "completions", "attempts", "rec_yds", "receptions",
                "rec_tds", "longest_rec", "anytime_td", "first_td",
            ]
            games_played = live_stats.get("_games", 0)
            for k in stat_keys:
                if live_stats.get(k) is not None and live_stats.get(k) != 0:
                    merged[k] = live_stats[k]
                else:
                    # Scale prior by expected role (starter vs backup)
                    merged[k] = prior.get(k, 0)

            # Fetch L5 mod (rate-limited — only for players with stats)
            if games_played >= 3:
                l5 = _fetch_l5_mod(pid, pos, merged)
            else:
                l5 = prior.get("_l5", 1.00)

            std, hr = _estimate_std_and_hr(merged, pos)
            tier    = _assign_tier(merged, pos)

            db[pid] = {
                "name":       name,
                "team":       team_abbr,
                "pos":        pos,
                "num":        player["num"],
                "tier":       tier,
                "espn_id":    pid,
                "games":      games_played,
                **{k: merged[k] for k in stat_keys},
                "std":        std,
                "l5":         l5,
                "hr":         hr,
            }
            fetched_players += 1

        # Small sleep to be polite to ESPN servers
        time.sleep(0.05)

    return db


# ── CACHED ACCESSOR (with graceful fallback) ──────────────────────────────────

_FALLBACK_DB_BUILT = False

def get_player_db() -> dict:
    """
    Return the live player DB, building it if needed.
    Falls back to the static DB if ESPN is unreachable.
    """
    global _FALLBACK_DB_BUILT
    try:
        db = build_live_player_db()
        if db:
            return db
    except Exception:
        pass

    # Hard fallback: import static DB from v2
    if not _FALLBACK_DB_BUILT:
        _FALLBACK_DB_BUILT = True
        try:
            from utils.player_db_static import PLAYER_DB
            return PLAYER_DB
        except ImportError:
            pass
    return {}


def get_player_db_with_progress() -> dict:
    """
    Build the live DB with a Streamlit progress bar.
    Call this from the app startup page only.
    """
    # Check if already cached
    try:
        cached = build_live_player_db()
        if cached:
            return cached
    except Exception:
        pass

    progress_bar = st.progress(0, text="Loading live NFL rosters from ESPN…")
    status_text  = st.empty()

    results = {}
    total = len(ESPN_TEAM_IDS)

    for i, (team_abbr, espn_id) in enumerate(ESPN_TEAM_IDS.items()):
        pct = int((i / total) * 100)
        progress_bar.progress(pct, text=f"Loading {team_abbr} roster… ({i+1}/{total} teams)")
        status_text.caption(f"Fetching live data for {team_abbr}…")

        roster = _fetch_team_roster(team_abbr, espn_id)
        for player in roster:
            pid  = player["espn_id"]
            pos  = player["pos"]
            live = _fetch_player_stats(pid, pos)
            prior = POSITION_PRIORS.get(pos, POSITION_PRIORS["WR"])
            merged = {}
            stat_keys = [
                "pass_yds","pass_tds","rush_yds","rush_att",
                "completions","attempts","rec_yds","receptions",
                "rec_tds","longest_rec","anytime_td","first_td",
            ]
            games = live.get("_games", 0)
            for k in stat_keys:
                merged[k] = live.get(k) or prior.get(k, 0)
            l5 = _fetch_l5_mod(pid, pos, merged) if games >= 3 else 1.00
            std, hr = _estimate_std_and_hr(merged, pos)
            results[pid] = {
                "name": player["name"], "team": team_abbr,
                "pos": pos, "num": player["num"],
                "tier": _assign_tier(merged, pos),
                "espn_id": pid, "games": games,
                **{k: merged[k] for k in stat_keys},
                "std": std, "l5": l5, "hr": hr,
            }
        time.sleep(0.05)

    progress_bar.progress(100, text="✅ All rosters loaded!")
    status_text.empty()
    return results


# ── Convenience: get single player ───────────────────────────────────────────

def get_player(player_id: str) -> dict | None:
    return get_player_db().get(player_id)
