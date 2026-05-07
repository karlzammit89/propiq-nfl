"""
PropIQ Statistical Engine
Multi-model prop projection with normal distribution probability math.
"""

import math
from dataclasses import dataclass, field
from typing import Optional
from utils.player_db import PLAYER_DB


# ── Probability math ──────────────────────────────────────────────────────────

def _erf(x: float) -> float:
    """Abramowitz & Stegun approximation of erf."""
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t)
                  + 1.421413741) * t - 0.284496736) * t
                + 0.254829592) * t * math.exp(-x * x)
    return sign * y


def norm_cdf(x: float, mean: float, std: float) -> float:
    if std <= 0:
        return 0.5
    return 0.5 * (1 + _erf((x - mean) / (std * math.sqrt(2))))


def to_american(p: float) -> str:
    p = max(0.01, min(0.99, p))
    if p > 0.5:
        return f"-{round(p / (p - 1) * 100)}"
    return f"+{round((1 - p) / p * 100)}"


def vig_american(p: float, vig: float = 0.046) -> str:
    return to_american(p * (1 + vig))


def decimal_odds(p: float) -> float:
    return round(1 / max(0.01, p), 2)


# ── Environment modifiers ─────────────────────────────────────────────────────

def _weather_mod(weather: str) -> float:
    w = weather.lower()
    if "dome" in w:
        return 1.02
    mod = 1.0
    if any(t in w for t in ["29°", "30°", "31°", "32°", "33°", "34°", "35°"]):
        mod *= 0.90
    elif any(t in w for t in ["36°", "37°", "38°", "39°", "40°"]):
        mod *= 0.93
    if "snow" in w:
        mod *= 0.84
    elif "rain" in w:
        mod *= 0.88
    if "15mph" in w or "16mph" in w or "17mph" in w or "18mph" in w or "20mph" in w:
        mod *= 0.88
    elif "12mph" in w or "13mph" in w or "14mph" in w:
        mod *= 0.93
    return mod


def _surface_mod(surface: str) -> float:
    return 1.03 if "turf" in surface.lower() else 1.0


def _home_mod(is_home: bool) -> float:
    return 1.04 if is_home else 0.96


def _ou_mod(ou: float) -> float:
    if ou > 50:
        return 1.10
    if ou > 48:
        return 1.06
    if ou < 40:
        return 0.92
    if ou < 42:
        return 0.96
    return 1.0


# ── Defense modifiers ─────────────────────────────────────────────────────────
LEAGUE_AVG_PASS_YD = 215.0
LEAGUE_AVG_RUSH_YD = 108.0
LEAGUE_AVG_PPA     = 0.052


def _def_pass_mod(def_pass_yd_pg: float) -> float:
    return def_pass_yd_pg / LEAGUE_AVG_PASS_YD


def _def_rush_mod(def_rush_yd_pg: float) -> float:
    return def_rush_yd_pg / LEAGUE_AVG_RUSH_YD


def _def_ppa_mod(ppa: float) -> float:
    return ppa / LEAGUE_AVG_PPA


# ── Snap / injury composite ───────────────────────────────────────────────────

def _availability(snap_pct: float, inj_status: Optional[str]) -> float:
    inj_map = {"Q": 0.88, "D": 0.65, "O": 0.0, None: 1.0, "": 1.0}
    inj_f = inj_map.get(inj_status, 1.0)
    snap_f = min(1.0, snap_pct / 0.85 + 0.10)  # normalize — >85% snap = full
    return inj_f * min(1.0, snap_f)


# ── Projection dataclass ──────────────────────────────────────────────────────

@dataclass
class PropResult:
    market:     str
    label:      str
    unit:       str
    projection: float
    line:       float
    std:        float
    over_prob:  float
    under_prob: float
    hit_rate:   float
    is_bool:    bool          = False  # anytime TD, first TD
    factors:    list          = field(default_factory=list)
    env_mod:    float         = 1.0
    def_mod:    float         = 1.0
    snap_mod:   float         = 1.0
    l5_mod:     float         = 1.0

    @property
    def fair_over(self) -> str:
        return to_american(self.over_prob)

    @property
    def fair_under(self) -> str:
        return to_american(self.under_prob)

    @property
    def vig_over(self) -> str:
        return vig_american(self.over_prob)

    @property
    def vig_under(self) -> str:
        return vig_american(self.under_prob)

    @property
    def confidence(self) -> str:
        e = abs(self.over_prob - 0.5)
        if e > 0.12:
            return "High"
        if e > 0.05:
            return "Medium"
        return "Low"

    @property
    def edge_direction(self) -> str:
        if self.over_prob > 0.54:
            return "OVER"
        if self.over_prob < 0.46:
            return "UNDER"
        return "NEUTRAL"

    @property
    def line_display(self) -> str:
        if self.is_bool:
            return f"{self.over_prob * 100:.1f}%"
        return str(int(self.line)) if self.line == int(self.line) else f"{self.line:.1f}"


# ── Main engine ───────────────────────────────────────────────────────────────

MARKET_META = {
    "pass_yds":   ("Passing Yards",       "yds"),
    "pass_tds":   ("Passing TDs",         "TDs"),
    "rush_yds":   ("Rushing Yards",       "yds"),
    "rush_att":   ("Rush Attempts",       "att"),
    "rec_yds":    ("Receiving Yards",     "yds"),
    "receptions": ("Receptions",          "rec"),
    "rec_tds":    ("Receiving TDs",       "TDs"),
    "completions":("Completions",         "comp"),
    "attempts":   ("Pass Attempts",       "att"),
    "anytime_td": ("Anytime TD",          "%"),
    "first_td":   ("1st TD Scorer",       "%"),
    "longest_rec":("Longest Reception",   "yds"),
}


def compute_props(
    player_id: str,
    markets: list,
    schedule: dict,
    defense: dict,
    snap_pct: float = 1.0,
    inj_status: Optional[str] = None,
) -> list[PropResult]:
    """
    Core projection engine. Returns list of PropResult objects.
    """
    st = PLAYER_DB.get(player_id)
    if not st:
        return []

    pos = st["pos"]

    # Modifiers
    env_m   = _weather_mod(schedule.get("weather", "Clear 65°F"))
    surf_m  = _surface_mod(schedule.get("surface", "Grass"))
    home_m  = _home_mod(schedule.get("home", True))
    ou_m    = _ou_mod(schedule.get("ou", 44.5))
    avail   = _availability(snap_pct, inj_status)
    l5      = st.get("l5", 1.0)

    def_pm  = _def_pass_mod(defense.get("pass_yd_pg", LEAGUE_AVG_PASS_YD))
    def_rm  = _def_rush_mod(defense.get("rush_yd_pg", LEAGUE_AVG_RUSH_YD))
    def_ppa = _def_ppa_mod(defense.get("ppa", LEAGUE_AVG_PPA))
    def_rec = (def_pm * 0.85 + surf_m * 0.15)  # receiving yards slightly surface-weighted

    results = []

    def proj_base(stat_key, def_mod, *extra_mods):
        base = st.get(stat_key, 0)
        if not base:
            return 0.0
        total = base * def_mod * env_m * home_m * l5 * avail
        for m in extra_mods:
            total *= m
        return total

    def snap_round(v, step=0.5):
        return round(v / step) * step

    def make_factors(def_mod, rush=False, td=False):
        tags = []
        if def_mod > 1.10:
            tags.append(("pos", f"Vulnerable defense (+{(def_mod-1)*100:.0f}%)"))
        elif def_mod < 0.90:
            tags.append(("neg", f"Elite defense ({(def_mod-1)*100:.0f}%)"))
        else:
            tags.append(("neu", "Neutral defense matchup"))

        if env_m < 0.90:
            tags.append(("neg", "Severe weather impact"))
        elif env_m < 0.96:
            tags.append(("neg", f"Weather factor ({env_m:.2f}x)"))
        elif env_m > 1.01:
            tags.append(("pos", "Dome boost (+2%)"))

        if surf_m > 1.0 and not rush:
            tags.append(("pos", "Turf surface (+3% pass)"))

        tags.append(("pos", "Home field") if home_m > 1 else ("neg", "Away game"))

        if ou_m > 1.04:
            tags.append(("pos", f"High-scoring game total ({schedule.get('ou','?')})"))
        elif ou_m < 0.96:
            tags.append(("neg", f"Low game total ({schedule.get('ou','?')})"))

        if l5 > 1.03:
            tags.append(("pos", f"Hot recent form (L5 +{(l5-1)*100:.1f}%)"))
        elif l5 < 0.97:
            tags.append(("neg", f"Cold recent form (L5 {(l5-1)*100:.1f}%)"))

        if inj_status == "Q":
            tags.append(("neg", f"Questionable — {round(avail*100)}% output adj"))
        elif inj_status == "D":
            tags.append(("neg", f"Doubtful — {round(avail*100)}% output adj"))

        if snap_pct < 0.65:
            tags.append(("neg", f"Snap share concern ({round(snap_pct*100)}%)"))

        return tags

    for market in markets:
        if market not in MARKET_META:
            continue
        label, unit = MARKET_META[market]
        res = None

        # ── QB markets ────────────────────────────────────────────────────────
        if market == "pass_yds" and pos == "QB":
            p = proj_base("pass_yds", def_pm, ou_m)
            if p:
                std  = st["std"].get("pass_yds", 55)
                line = round(p / 5) * 5
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op,
                                  st["hr"].get("pass_yds", 0.60),
                                  factors=make_factors(def_pm),
                                  env_mod=env_m, def_mod=def_pm, l5_mod=l5)

        elif market == "pass_tds" and pos == "QB":
            p = proj_base("pass_tds", def_pm, ou_m)
            if p:
                std  = st["std"].get("pass_tds", 0.9)
                line = snap_round(p, 0.5)
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op,
                                  st["hr"].get("pass_tds", 0.58),
                                  factors=make_factors(def_pm),
                                  env_mod=env_m, def_mod=def_pm, l5_mod=l5)

        elif market == "completions" and pos == "QB":
            p = proj_base("completions", def_pm)
            if p:
                std  = st["std"].get("completions", 3.5)
                line = snap_round(p)
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op,
                                  st["hr"].get("completions", 0.60),
                                  factors=make_factors(def_pm),
                                  env_mod=env_m, def_mod=def_pm, l5_mod=l5)

        elif market == "attempts" and pos == "QB":
            p = proj_base("attempts", def_pm)
            if p:
                std  = st["std"].get("attempts", 4.5)
                line = snap_round(p)
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op,
                                  st["hr"].get("attempts", 0.60),
                                  factors=make_factors(def_pm),
                                  env_mod=env_m, def_mod=def_pm, l5_mod=l5)

        # ── Rush markets ──────────────────────────────────────────────────────
        elif market == "rush_yds":
            base = st.get("rush_yds", 0)
            if base and base >= 5:
                p    = proj_base("rush_yds", def_rm)
                std  = st["std"].get("rush_yds", 26)
                line = round(p / 5) * 5
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op,
                                  st["hr"].get("rush_yds", 0.58),
                                  factors=make_factors(def_rm, rush=True),
                                  env_mod=env_m, def_mod=def_rm, l5_mod=l5)

        elif market == "rush_att":
            base = st.get("rush_att", 0)
            if base and base >= 1:
                p    = proj_base("rush_att", def_rm)
                std  = st["std"].get("rush_att", 2.6)
                line = snap_round(p)
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op,
                                  st["hr"].get("rush_att", 0.60),
                                  factors=make_factors(def_rm, rush=True),
                                  env_mod=env_m, def_mod=def_rm, l5_mod=l5)

        # ── Receiving markets ─────────────────────────────────────────────────
        elif market == "rec_yds":
            base = st.get("rec_yds", 0)
            if base:
                p    = proj_base("rec_yds", def_rec, surf_m)
                std  = st["std"].get("rec_yds", 24)
                line = round(p / 5) * 5
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op,
                                  st["hr"].get("rec_yds", 0.60),
                                  factors=make_factors(def_rec),
                                  env_mod=env_m, def_mod=def_rec, l5_mod=l5)

        elif market == "receptions":
            base = st.get("receptions", 0)
            if base:
                p    = proj_base("receptions", def_rec)
                std  = st["std"].get("receptions", 1.8)
                line = snap_round(p)
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op,
                                  st["hr"].get("receptions", 0.60),
                                  factors=make_factors(def_rec),
                                  env_mod=env_m, def_mod=def_rec, l5_mod=l5)

        elif market == "rec_tds":
            base = st.get("rec_tds", 0)
            if base:
                p_raw = (base * def_ppa * home_m * l5 * avail)
                op    = min(0.92, p_raw * 2.4)
                res   = PropResult(market, label, unit, p_raw, 0.5, 0, op, 1-op,
                                   st["hr"].get("rec_tds", 0.34), is_bool=True,
                                   factors=make_factors(def_ppa, td=True),
                                   env_mod=env_m, def_mod=def_ppa, l5_mod=l5)

        elif market == "longest_rec":
            base = st.get("longest_rec", 0)
            if base:
                p    = proj_base("longest_rec", def_rec, surf_m)
                std  = p * 0.42
                line = round(p / 5) * 5
                op   = 1 - norm_cdf(line, p, std)
                res  = PropResult(market, label, unit, p, line, std, op, 1-op, 0.52,
                                  factors=make_factors(def_rec),
                                  env_mod=env_m, def_mod=def_rec, l5_mod=l5)

        # ── TD booleans ───────────────────────────────────────────────────────
        elif market == "anytime_td":
            base = st.get("anytime_td", 0)
            if base:
                p  = min(0.95, base * def_ppa * home_m * (l5 ** 0.5) * avail)
                hr = 0.68 if p > 0.70 else (0.58 if p > 0.55 else 0.45)
                res = PropResult(market, label, unit, p, None, 0, p, 1-p, hr,
                                 is_bool=True,
                                 factors=make_factors(def_ppa, td=True),
                                 env_mod=env_m, def_mod=def_ppa, l5_mod=l5)

        elif market == "first_td":
            base = st.get("first_td", 0)
            if base:
                p  = min(0.55, base * def_ppa * home_m * (l5 ** 0.5) * avail)
                hr = 0.24 if base > 0.22 else 0.18
                res = PropResult(market, label, unit, p, None, 0, p, 1-p, hr,
                                 is_bool=True,
                                 factors=make_factors(def_ppa, td=True),
                                 env_mod=env_m, def_mod=def_ppa, l5_mod=l5)

        if res:
            res.snap_mod = avail
            results.append(res)

    return results


# ── Correlation engine ────────────────────────────────────────────────────────

CORR_PASSING_RECV = 1    # QB pass yds + same-team WR/TE rec yds  → positive
CORR_PASS_RECV_TD = 2    # QB pass TDs + same-team WR/TE rec TDs  → strong positive
CORR_QB_RB_NEG    = -1   # QB pass yds + same-team RB rush yds    → negative
CORR_SAME_POS     = -0.5 # Same team same position                 → slight negative
CORR_ANYTIME_GAME = 0.5  # Opposing team both anytime TD          → game total corr


def get_correlation(leg_a: dict, leg_b: dict) -> dict:
    """
    Detect correlation between two parlay legs.
    Each leg dict must have: {player_id, market, team, pos}
    Returns: {label, cls, value}
    """
    same_team = leg_a["team"] == leg_b["team"]
    sched = FALLBACK_SCHEDULES if True else {}  # always use for team lookup
    # same game = same team OR a vs b
    a_opp = _get_opp(leg_a["team"])
    same_game = same_team or (a_opp == leg_b["team"])

    if not same_game:
        return {"label": "Uncorrelated", "cls": "neu", "value": 0}

    am, bm = leg_a["market"], leg_b["market"]
    ap, bp = leg_a["pos"], leg_b["pos"]

    # QB + WR/TE same team → positive
    if same_team:
        passing_markets = {"pass_yds", "pass_tds", "completions", "attempts"}
        recv_markets    = {"rec_yds", "receptions", "rec_tds"}
        if (am in passing_markets and bp in ("WR", "TE")) or \
           (bm in passing_markets and ap in ("WR", "TE")):
            strength = CORR_PASS_RECV_TD if (am == "pass_tds" or bm == "pass_tds") else CORR_PASSING_RECV
            cls = "corr-pos"
            lbl = "Strong positive corr" if strength == 2 else "Positive correlation"
            return {"label": lbl, "cls": cls, "value": strength}

        # QB + RB rush → negative (game script)
        if ((ap == "QB" and bm == "rush_yds") or (bp == "QB" and am == "rush_yds")):
            return {"label": "Negative correlation (game script)", "cls": "corr-neg", "value": CORR_QB_RB_NEG}

        # Same team same position
        if ap == bp and ap in ("WR", "RB", "TE"):
            return {"label": "Slight negative (shared targets)", "cls": "corr-neg", "value": CORR_SAME_POS}

    # Both anytime TDs opposite team → game total
    if not same_team and same_game and am == "anytime_td" and bm == "anytime_td":
        return {"label": "Game total correlation", "cls": "corr-pos", "value": CORR_ANYTIME_GAME}

    return {"label": "Low correlation", "cls": "neu", "value": 0}


def _get_opp(team: str) -> str:
    from utils.fallback_data import FALLBACK_SCHEDULES
    return FALLBACK_SCHEDULES.get(team, {}).get("opp", "")


def compute_parlay(legs: list) -> dict:
    """
    Given list of parlay leg dicts, compute combined odds, true probability,
    and correlation-adjusted probability.
    Each leg: {player_id, player_name, market, team, pos, over_prob, line, is_bool}
    """
    if not legs:
        return {}

    # Independent combined probability
    indep_prob = 1.0
    for leg in legs:
        indep_prob *= leg["over_prob"]

    # Combined decimal odds (from book implied probs)
    combined_decimal = 1.0
    for leg in legs:
        combined_decimal *= decimal_odds(leg["over_prob"])

    # Correlation adjustment
    corr_adj = 0.0
    corr_pairs = []
    for i in range(len(legs)):
        for j in range(i + 1, len(legs)):
            corr = get_correlation(legs[i], legs[j])
            if corr["value"] != 0:
                corr_pairs.append({"i": i, "j": j, "corr": corr})
                corr_adj += corr["value"] * 0.012

    adj_prob = min(0.98, indep_prob * (1 + corr_adj))

    payout_am = to_american(1 / combined_decimal)
    payout_100 = round(combined_decimal * 100)

    return {
        "legs":             len(legs),
        "combined_decimal": combined_decimal,
        "payout_american":  payout_am,
        "payout_100":       payout_100,
        "indep_prob":       indep_prob,
        "adj_prob":         adj_prob,
        "corr_pairs":       corr_pairs,
        "has_positive_corr": any(cp["corr"]["value"] > 0 for cp in corr_pairs),
        "has_negative_corr": any(cp["corr"]["value"] < 0 for cp in corr_pairs),
    }


# Import for correlation engine
from utils.fallback_data import FALLBACK_SCHEDULES
