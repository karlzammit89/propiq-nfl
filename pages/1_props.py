"""Page 1 — Prop Generator"""
import streamlit as st
from utils.player_db import PLAYER_DB
from utils.api import fetch_schedule, fetch_defense_ratings, fetch_injury_report, fetch_snap_counts, fetch_live_odds
from utils.engine import compute_props, MARKET_META
from utils.fallback_data import FALLBACK_INJURIES, FALLBACK_SNAPS

st.markdown("## 🏈 Prop Generator")
st.caption("Select a player · auto-loads matchup, defense, weather, and live odds")

keys = st.session_state.api_keys

# ── Sidebar: Player selection ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Player Selection")
    pos_filter = st.selectbox("Position", ["ALL", "QB", "RB", "WR", "TE"])
    search = st.text_input("Search name or team", placeholder="e.g. Mahomes, KC, WR...")

    # Build filtered list
    filtered = {
        pid: p for pid, p in PLAYER_DB.items()
        if (pos_filter == "ALL" or p["pos"] == pos_filter)
        and (not search or search.lower() in p["name"].lower() or search.lower() in p["team"].lower())
    }

    pos_icons = {"QB": "🟣", "RB": "🟢", "WR": "🟡", "TE": "🔵"}
    player_options = {
        pid: f"{pos_icons.get(p['pos'], '')} {p['name']} · {p['team']}"
        for pid, p in filtered.items()
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

    st.markdown("---")
    st.markdown("### Markets")
    all_markets = list(MARKET_META.keys())
    selected_mkts = st.multiselect(
        "Select markets to generate",
        options=all_markets,
        default=["pass_yds", "pass_tds", "rush_yds", "rec_yds", "anytime_td"],
        format_func=lambda m: MARKET_META[m][0],
    )

    generate = st.button("⚡ Generate Props", use_container_width=True)


# ── Main: Auto-load on player change or button press ─────────────────────────
if not generate and "prop_results" not in st.session_state:
    st.info("👈 Select a player and click **Generate Props** to begin.")
    st.stop()

if generate or "prop_results" not in st.session_state:
    player = PLAYER_DB[selected_id]
    team = player["team"]

    with st.spinner("Loading matchup data, defense ratings, and live odds..."):
        schedule = fetch_schedule(team, keys["sportradar"])
        defense  = fetch_defense_ratings(schedule["opp"], keys["sportradar"])
        injuries = fetch_injury_report(keys["fantasy_life"])

        # Snap count lookup
        snaps_team = fetch_snap_counts(team, keys["sportradar"])
        snap_pct = snaps_team.get(player["name"], 0.85)
        if snap_pct == 0:
            snap_pct = 0.85  # default if not found

        # Injury status
        inj_data = injuries.get(player["name"], {})
        inj_status = inj_data.get("status", None)
        inj_note   = inj_data.get("note", "")

        results = compute_props(selected_id, selected_mkts, schedule, defense, snap_pct, inj_status)

    st.session_state.prop_results = {
        "player": player, "schedule": schedule, "defense": defense,
        "results": results, "snap_pct": snap_pct,
        "inj_status": inj_status, "inj_note": inj_note,
    }

data = st.session_state.get("prop_results", {})
if not data:
    st.stop()

player   = data["player"]
schedule = data["schedule"]
defense  = data["defense"]
results  = data["results"]
snap_pct = data["snap_pct"]
inj_status = data["inj_status"]
inj_note   = data["inj_note"]
opp = schedule.get("opp", "TBD")

# ── Matchup Hero Card ─────────────────────────────────────────────────────────
with st.container():
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        st.markdown(f"### {player['name']}")
        st.caption(f"{player['team']} · {player['pos']} · #{player['num']}")
        if inj_status:
            badge = {"Q": "🟡 Questionable", "D": "🔴 Doubtful", "O": "⛔ OUT"}.get(inj_status, "")
            st.markdown(f"**{badge}** — {inj_note}")
        st.markdown(f"**Snap Share:** {round(snap_pct * 100)}%")
        st.progress(snap_pct)

    with c2:
        home_away = "vs" if schedule.get("home") else "@"
        st.markdown(f"### {home_away} **{opp}**")
        st.caption(f"{schedule.get('stadium','TBD')}")
        st.markdown(f"🌤 {schedule.get('weather','N/A')}")
        st.markdown(f"🏟 {schedule.get('surface','Grass')}  |  O/U: **{schedule.get('ou','?')}**  |  Spread: **{schedule.get('spread',0)}**")

    with c3:
        st.markdown("### Defense Ratings")
        dr = defense
        def rank_color(r):
            if r <= 8: return "🟢"
            if r <= 16: return "🔵"
            if r <= 24: return "🟡"
            return "🔴"
        st.markdown(f"{rank_color(dr.get('pass_rank',16))} **Pass Yds/G:** {dr.get('pass_yd_pg','?')} (#{dr.get('pass_rank','?')})")
        st.markdown(f"{rank_color(dr.get('rush_rank',16))} **Rush Yds/G:** {dr.get('rush_yd_pg','?')} (#{dr.get('rush_rank','?')})")
        st.markdown(f"📊 **Points/Play:** {dr.get('ppa', 0.052):.3f}")

st.divider()

# ── Prop Cards ────────────────────────────────────────────────────────────────
if not results:
    st.warning("No props generated. The selected markets may not apply to this player's position.")
    st.stop()

st.markdown(f"### {len(results)} Prop Markets · {player['name']}")

for res in results:
    conf_color = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(res.confidence, "⚪")
    edge_arrow = "▲ OVER" if res.over_prob > 0.54 else ("▼ UNDER" if res.over_prob < 0.46 else "↔ NEUTRAL")

    with st.expander(
        f"{conf_color} **{res.label}** — {edge_arrow} · {res.confidence} confidence",
        expanded=(res.confidence == "High")
    ):
        # Odds row
        c1, c2, c3 = st.columns(3)
        if res.is_bool:
            with c1:
                st.metric("True Probability", f"{res.over_prob * 100:.1f}%")
            with c2:
                st.metric("Yes Odds (with vig)", res.vig_over, delta=f"Fair: {res.fair_over}")
            with c3:
                st.metric("No Odds (with vig)", res.vig_under)
        else:
            with c1:
                st.metric("Projection", f"{res.projection:.1f} {res.unit}")
            with c2:
                st.metric(f"Over {res.line_display}", res.vig_over,
                          delta=f"Fair: {res.fair_over} | {res.over_prob*100:.1f}%")
            with c3:
                st.metric(f"Under {res.line_display}", res.vig_under,
                          delta=f"{res.under_prob*100:.1f}%")

        # Live odds comparison
        st.markdown("**📡 Live Odds Comparison**")
        live = fetch_live_odds(player["name"], res.market, keys["odds_api"])
        if live:
            book_cols = st.columns(min(5, len(live)))
            best_over_p = min(v.get("overP", 0.5) for v in live.values())
            for i, (book, odds) in enumerate(list(live.items())[:5]):
                with book_cols[i % len(book_cols)]:
                    is_best = abs(odds.get("overP", 0.5) - best_over_p) < 0.001
                    border = "🏆 " if is_best else ""
                    st.markdown(f"**{border}{book}**")
                    if not res.is_bool:
                        st.markdown(f"O: `{odds.get('over', '—')}`")
                        st.markdown(f"U: `{odds.get('under', '—')}`")
                    else:
                        st.markdown(f"Yes: `{odds.get('over', '—')}`")
                st.caption(f"Fair: {res.fair_over} over")

        # Distribution bar
        st.markdown("**Probability Distribution**")
        prob_col1, prob_col2 = st.columns([res.under_prob, res.over_prob])
        with prob_col1:
            st.markdown(f"🔴 Under: **{res.under_prob*100:.1f}%**")
        with prob_col2:
            st.markdown(f"🟢 Over: **{res.over_prob*100:.1f}%**")
        st.progress(res.over_prob)

        # Hit rates
        st.markdown("**📈 Historical Hit Rate**")
        hr_c1, hr_c2, hr_c3, hr_c4 = st.columns(4)
        with hr_c1:
            st.metric("Season HR", f"{res.hit_rate*100:.0f}%")
        with hr_c2:
            l5_hr = min(1.0, res.hit_rate * res.l5_mod)
            st.metric("L5 Form", f"{l5_hr*100:.0f}%")
        with hr_c3:
            matchup_hr = min(1.0, res.hit_rate * res.def_mod)
            st.metric("Matchup Adj", f"{matchup_hr*100:.0f}%")
        with hr_c4:
            edge_pct = abs(res.over_prob - 0.5) * 200
            st.metric("Model Edge", f"{edge_pct:.0f}%")

        # Factors
        st.markdown("**Key Factors**")
        factor_parts = []
        for cls, text in res.factors:
            icon = {"pos": "✅", "neg": "⚠️", "neu": "ℹ️"}.get(cls, "")
            factor_parts.append(f"{icon} {text}")
        st.markdown("  ·  ".join(factor_parts))

        # Add to parlay
        parlay_key = f"{selected_id}_{res.market}"
        already_in = any(l["key"] == parlay_key for l in st.session_state.parlay_legs)
        if not already_in:
            if st.button(f"➕ Add to Parlay", key=f"add_{parlay_key}"):
                st.session_state.parlay_legs.append({
                    "key":         parlay_key,
                    "player_id":   selected_id,
                    "player_name": player["name"],
                    "market":      res.market,
                    "market_label":res.label,
                    "team":        player["team"],
                    "pos":         player["pos"],
                    "over_prob":   res.over_prob,
                    "line":        res.line or 0,
                    "is_bool":     res.is_bool,
                    "line_display":res.line_display,
                    "vig_over":    res.vig_over,
                })
                st.success(f"Added {res.label} to parlay! ({len(st.session_state.parlay_legs)} legs)")
                st.rerun()
        else:
            st.caption("✅ Already in parlay")
