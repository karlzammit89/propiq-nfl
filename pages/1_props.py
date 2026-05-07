"""Page 1 — Prop Generator (live ESPN roster + stats)"""
import streamlit as st
from utils.api import (
    fetch_schedule,
    fetch_defense_ratings,
    fetch_prop_odds,
    get_player_status,
)
from utils.engine import compute_props, MARKET_META

st.markdown("## 🏈 Prop Generator")
st.caption("Live ESPN rosters · current stats · RotoWire inactives · always up to date")

# ── Get live player DB from session state ─────────────────────────────────────
PLAYER_DB = st.session_state.get("live_player_db", {})

if not PLAYER_DB:
    st.error("Player database not loaded. Please refresh the page.")
    st.stop()

db_size = st.session_state.get("player_db_size", len(PLAYER_DB))
st.caption(f"✅ {db_size} active NFL skill players loaded live from ESPN")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Player Selection")

    pos_filter = st.selectbox("Position", ["ALL", "QB", "RB", "WR", "TE"])
    search     = st.text_input("Search name or team", placeholder="e.g. Williams, DEN…")
    tier_filter = st.selectbox(
        "Show players",
        ["Starters only (Tier 1)", "Starters + Rotational", "All players"],
        index=1,
    )
    tier_max = 1 if "Tier 1" in tier_filter else (2 if "Rotational" in tier_filter else 3)

    filtered = {
        pid: p for pid, p in PLAYER_DB.items()
        if (pos_filter == "ALL" or p["pos"] == pos_filter)
        and (not search or search.lower() in p["name"].lower()
             or search.lower() in p["team"].lower())
        and p.get("tier", 3) <= tier_max
    }

    # Sort: by team, then position, then name
    sorted_players = sorted(
        filtered.items(),
        key=lambda x: (x[1]["team"], x[1]["pos"], x[1]["name"])
    )

    pos_icons = {"QB": "🟣", "RB": "🟢", "WR": "🟡", "TE": "🔵"}
    player_options = {
        pid: f"{pos_icons.get(p['pos'],'')} {p['name']} · {p['team']}"
        for pid, p in sorted_players
    }

    if not player_options:
        st.warning("No players match your filter.")
        st.stop()

    selected_id = st.selectbox(
        "Player",
        options=list(player_options.keys()),
        format_func=lambda x: player_options[x],
    )
    st.session_state.selected_player = selected_id

    # Show player quick info
    sel = PLAYER_DB.get(selected_id, {})
    if sel:
        games = sel.get("games", 0)
        if games > 0:
            st.caption(f"📊 {games} games played this season (ESPN live data)")
        else:
            st.caption("📊 No stats yet this season — using position averages")

    st.markdown("---")
    st.markdown("### Markets")
    selected_mkts = st.multiselect(
        "Select markets",
        options=list(MARKET_META.keys()),
        default=["pass_yds", "pass_tds", "rush_yds", "rec_yds", "anytime_td"],
        format_func=lambda m: MARKET_META[m][0],
    )

    generate = st.button("⚡ Generate Props", use_container_width=True)

    # Manual roster refresh
    st.markdown("---")
    if st.button("🔄 Refresh Rosters", use_container_width=True, help="Pulls fresh rosters from ESPN (takes ~60 sec)"):
        from utils.roster import build_live_player_db
        build_live_player_db.clear()
        st.session_state.player_db_loaded = False
        st.rerun()

# ── Generate ──────────────────────────────────────────────────────────────────
if not generate and "prop_results" not in st.session_state:
    st.info("👈 Select a player and click **Generate Props** to begin.")
    st.stop()

if generate or "prop_results" not in st.session_state:
    player = PLAYER_DB.get(selected_id)
    if not player:
        st.error("Player not found in live database. Try refreshing rosters.")
        st.stop()

    team = player["team"]

    with st.spinner(f"Loading live matchup data for {player['name']}…"):
        schedule = fetch_schedule(team)
        opp      = schedule.get("opp", "TBD")
        defense  = fetch_defense_ratings(opp)
        status   = get_player_status(player["name"], team)

        snap_pct   = status["snap_pct"]
        inj_status = status["status"]
        inj_note   = status["note"]
        inj_source = status["source"]

        results = compute_props(
            selected_id, selected_mkts,
            schedule, defense,
            snap_pct, inj_status,
        )

    st.session_state.prop_results = {
        "player": player, "schedule": schedule, "defense": defense,
        "results": results, "snap_pct": snap_pct,
        "inj_status": inj_status, "inj_note": inj_note,
        "inj_source": inj_source,
    }

data = st.session_state.get("prop_results", {})
if not data:
    st.stop()

player     = data["player"]
schedule   = data["schedule"]
defense    = data["defense"]
results    = data["results"]
snap_pct   = data["snap_pct"]
inj_status = data["inj_status"]
inj_note   = data["inj_note"]
inj_source = data.get("inj_source", "")
opp        = schedule.get("opp", "TBD")

# ── Matchup Hero ──────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 2, 2])

with c1:
    st.markdown(f"### {player['name']}")
    st.caption(f"{player['team']} · {player['pos']} · #{player.get('num','—')}")

    if inj_status == "O":
        st.error("⛔ INACTIVE — Do not bet this player")
    elif inj_status == "D":
        st.warning(f"🔴 Doubtful — {inj_note}  *(src: {inj_source})*")
    elif inj_status == "Q":
        st.warning(f"🟡 Questionable — {inj_note}  *(src: {inj_source})*")
    else:
        st.success(f"✅ Active  *(src: {inj_source})*")

    st.markdown(f"**Snap share:** {round(snap_pct * 100)}%")
    st.progress(min(1.0, snap_pct))

    games = player.get("games", 0)
    if games >= 3:
        l5 = player.get("l5", 1.00)
        form = f"+{(l5-1)*100:.1f}%" if l5 >= 1 else f"{(l5-1)*100:.1f}%"
        st.caption(f"📈 L5 form: {form} vs season avg  |  {games} games played")
    else:
        st.caption("📊 Limited game data — using position priors")

with c2:
    home_away = "vs" if schedule.get("home") else "@"
    st.markdown(f"### {home_away} **{opp}**")
    st.caption(schedule.get("stadium", "TBD"))
    st.markdown(f"🌤 `{schedule.get('weather','N/A')}`")
    spread = schedule.get("spread", 0)
    spread_str = f"+{spread}" if spread > 0 else str(spread)
    st.markdown(
        f"🏟 **{schedule.get('surface','Grass')}** &nbsp;|&nbsp; "
        f"O/U: **{schedule.get('ou','?')}** &nbsp;|&nbsp; "
        f"Spread: **{spread_str}**"
    )

with c3:
    st.markdown("### Defense Ratings")
    dr = defense
    def rc(r): return "🟢" if r<=8 else ("🔵" if r<=16 else ("🟡" if r<=24 else "🔴"))
    st.markdown(f"{rc(dr.get('pass_rank',16))} **Pass Yds/G:** {dr.get('pass_yd_pg','?')} (#{dr.get('pass_rank','?')})")
    st.markdown(f"{rc(dr.get('rush_rank',16))} **Rush Yds/G:** {dr.get('rush_yd_pg','?')} (#{dr.get('rush_rank','?')})")
    st.markdown(f"📊 **Pts/Play:** `{dr.get('ppa',0.052):.3f}`")
    st.caption("Source: ESPN live stats")

st.divider()

# ── INACTIVE BLOCK ────────────────────────────────────────────────────────────
if inj_status == "O":
    st.error("⛔ **INACTIVE.** Props suppressed. Do not bet this player today.")
    st.stop()

# ── Prop Cards ────────────────────────────────────────────────────────────────
if not results:
    st.warning("No props generated — selected markets may not apply to this position, or this player has no stats yet.")
    st.stop()

st.markdown(f"### {len(results)} Markets · {player['name']} {home_away} {opp}")

for res in results:
    conf_icon = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(res.confidence, "⚪")
    edge_txt  = "▲ OVER" if res.over_prob > 0.54 else ("▼ UNDER" if res.over_prob < 0.46 else "↔ NEUTRAL")

    with st.expander(
        f"{conf_icon} **{res.label}** — {edge_txt} · {res.confidence} confidence",
        expanded=(res.confidence == "High"),
    ):
        # Core odds
        c1, c2, c3 = st.columns(3)
        if res.is_bool:
            c1.metric("True Probability", f"{res.over_prob*100:.1f}%")
            c2.metric("Yes Odds", res.vig_over, delta=f"Fair: {res.fair_over}")
            c3.metric("No Odds", res.vig_under)
        else:
            c1.metric("Projection", f"{res.projection:.1f} {res.unit}")
            c2.metric(f"Over {res.line_display}", res.vig_over,
                      delta=f"Fair: {res.fair_over} | {res.over_prob*100:.1f}%")
            c3.metric(f"Under {res.line_display}", res.vig_under,
                      delta=f"{res.under_prob*100:.1f}%")

        # Book odds
        st.markdown("**📡 Book Odds** *(PropIQ model pricing — cross-check your sportsbook)*")
        live = fetch_prop_odds(player["name"], res.market, res.over_prob)
        if live:
            best_over_p = min(v["overP"] for v in live.values())
            cols = st.columns(len(live))
            for i, (book, odds) in enumerate(live.items()):
                is_best = abs(odds["overP"] - best_over_p) < 0.001
                with cols[i]:
                    st.markdown(f"**{'🏆 ' if is_best else ''}{book}**")
                    st.markdown(f"O: `{odds['over']}`")
                    st.markdown(f"U: `{odds['under']}`")

        # Distribution
        st.markdown("**Probability Distribution**")
        st.progress(res.over_prob)
        dc1, dc2 = st.columns(2)
        dc1.markdown(f"🔴 Under: **{res.under_prob*100:.1f}%**")
        dc2.markdown(f"🟢 Over: **{res.over_prob*100:.1f}%**")

        # Hit rates
        st.markdown("**📈 Historical Hit Rate**")
        hr1, hr2, hr3, hr4 = st.columns(4)
        hr1.metric("Season HR",   f"{res.hit_rate*100:.0f}%")
        hr2.metric("L5 Form",     f"{min(100, res.hit_rate*res.l5_mod*100):.0f}%")
        hr3.metric("Matchup Adj", f"{min(100, res.hit_rate*res.def_mod*100):.0f}%")
        hr4.metric("Model Edge",  f"{abs(res.over_prob-0.5)*200:.0f}%")

        # Factors
        st.markdown("**Key Factors**")
        icons = {"pos": "✅", "neg": "⚠️", "neu": "ℹ️"}
        st.markdown("  ·  ".join(f"{icons.get(c,'')} {t}" for c, t in res.factors))

        # Add to parlay
        parlay_key = f"{selected_id}_{res.market}"
        already_in = any(l["key"] == parlay_key for l in st.session_state.parlay_legs)
        if not already_in:
            if st.button(f"➕ Add to Parlay", key=f"add_{parlay_key}"):
                st.session_state.parlay_legs.append({
                    "key":          parlay_key,
                    "player_id":    selected_id,
                    "player_name":  player["name"],
                    "market":       res.market,
                    "market_label": res.label,
                    "team":         player["team"],
                    "pos":          player["pos"],
                    "over_prob":    res.over_prob,
                    "line":         res.line or 0,
                    "is_bool":      res.is_bool,
                    "line_display": res.line_display,
                    "vig_over":     res.vig_over,
                })
                st.success(f"Added {res.label} · {len(st.session_state.parlay_legs)} legs total")
                st.rerun()
        else:
            st.caption("✅ Already in parlay")
