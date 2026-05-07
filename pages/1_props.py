"""Page 1 — Prop Generator (fully free data layer)"""
import streamlit as st
from utils.player_db import PLAYER_DB
from utils.api import (
    fetch_schedule,
    fetch_defense_ratings,
    fetch_rotowire_inactives,
    fetch_espn_injuries,
    fetch_snap_counts,
    fetch_prop_odds,
    get_player_status,
)
from utils.engine import compute_props, MARKET_META

st.markdown("## 🏈 Prop Generator")
st.caption("Live data · ESPN public API · RotoWire inactives · Open-Meteo weather · 100% free")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Player Selection")
    pos_filter = st.selectbox("Position", ["ALL", "QB", "RB", "WR", "TE"])
    search = st.text_input("Search name or team", placeholder="e.g. Mahomes, KC…")

    filtered = {
        pid: p for pid, p in PLAYER_DB.items()
        if (pos_filter == "ALL" or p["pos"] == pos_filter)
        and (not search or search.lower() in p["name"].lower()
             or search.lower() in p["team"].lower())
    }

    pos_icons = {"QB": "🟣", "RB": "🟢", "WR": "🟡", "TE": "🔵"}
    player_options = {
        pid: f"{pos_icons.get(p['pos'],'')} {p['name']} · {p['team']}"
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
    selected_mkts = st.multiselect(
        "Select markets",
        options=list(MARKET_META.keys()),
        default=["pass_yds", "pass_tds", "rush_yds", "rec_yds", "anytime_td"],
        format_func=lambda m: MARKET_META[m][0],
    )

    generate = st.button("⚡ Generate Props", use_container_width=True)

# ── Generate ──────────────────────────────────────────────────────────────────
if not generate and "prop_results" not in st.session_state:
    col1, col2 = st.columns(2)
    with col1:
        st.info("👈 Select a player and click **Generate Props** to begin.")
    with col2:
        with st.container():
            st.markdown("**📡 Live data sources (all free)**")
            st.markdown("✅ ESPN public API — schedule, defense, injuries")
            st.markdown("✅ RotoWire — game-day inactives & status")
            st.markdown("✅ Open-Meteo — live weather")
            st.markdown("✅ PropIQ model — prop odds pricing")
    st.stop()

if generate or "prop_results" not in st.session_state:
    player = PLAYER_DB[selected_id]
    team   = player["team"]

    with st.spinner(f"Loading live data for {player['name']}…"):
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
    st.caption(f"{player['team']} · {player['pos']} · #{player['num']}")

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
    def rc(r):
        return "🟢" if r<=8 else ("🔵" if r<=16 else ("🟡" if r<=24 else "🔴"))
    st.markdown(f"{rc(dr.get('pass_rank',16))} **Pass Yds/G:** {dr.get('pass_yd_pg','?')} (#{dr.get('pass_rank','?')})")
    st.markdown(f"{rc(dr.get('rush_rank',16))} **Rush Yds/G:** {dr.get('rush_yd_pg','?')} (#{dr.get('rush_rank','?')})")
    st.markdown(f"📊 **Pts/Play:** `{dr.get('ppa',0.052):.3f}`")
    st.caption("Source: ESPN public API")

st.divider()

# ── INACTIVE WARNING ──────────────────────────────────────────────────────────
if inj_status == "O":
    st.error(
        "⛔ **This player is listed as INACTIVE.** "
        "Props have been suppressed to zero. Do not place bets on this player today."
    )
    st.stop()

# ── Prop Cards ────────────────────────────────────────────────────────────────
if not results:
    st.warning("No props generated — selected markets may not apply to this position.")
    st.stop()

st.markdown(f"### {len(results)} Markets · {player['name']} {home_away} {opp}")

for res in results:
    conf_icon = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(res.confidence, "⚪")
    edge_txt  = "▲ OVER" if res.over_prob > 0.54 else ("▼ UNDER" if res.over_prob < 0.46 else "↔ NEUTRAL")

    with st.expander(
        f"{conf_icon} **{res.label}** — {edge_txt} · {res.confidence} confidence",
        expanded=(res.confidence == "High"),
    ):
        # ── Core odds row ──────────────────────────────────────────────────
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

        # ── Book odds comparison ───────────────────────────────────────────
        st.markdown("**📡 Book Odds Comparison** *(PropIQ model pricing)*")
        live = fetch_prop_odds(player["name"], res.market, res.over_prob)
        if live:
            best_over_p = min(v["overP"] for v in live.values())
            cols = st.columns(len(live))
            for i, (book, odds) in enumerate(live.items()):
                is_best = abs(odds["overP"] - best_over_p) < 0.001
                label   = f"🏆 {book}" if is_best else book
                with cols[i]:
                    st.markdown(f"**{label}**")
                    over_tag  = f"O: `{odds['over']}`"
                    under_tag = f"U: `{odds['under']}`"
                    st.markdown(over_tag)
                    st.markdown(under_tag)
            st.caption(
                "ℹ️ ESPN doesn't publish player-prop lines publicly. "
                "Odds above are PropIQ's fair model price + realistic per-book vig/offset. "
                "Cross-check with your sportsbook before betting."
            )

        # ── Distribution ───────────────────────────────────────────────────
        st.markdown("**Probability Distribution**")
        st.progress(res.over_prob)
        dc1, dc2 = st.columns(2)
        dc1.markdown(f"🔴 Under: **{res.under_prob*100:.1f}%**")
        dc2.markdown(f"🟢 Over: **{res.over_prob*100:.1f}%**")

        # ── Hit rates ──────────────────────────────────────────────────────
        st.markdown("**📈 Historical Hit Rate**")
        hr1, hr2, hr3, hr4 = st.columns(4)
        hr1.metric("Season HR",   f"{res.hit_rate*100:.0f}%")
        hr2.metric("L5 Form",     f"{min(100, res.hit_rate*res.l5_mod*100):.0f}%")
        hr3.metric("Matchup Adj", f"{min(100, res.hit_rate*res.def_mod*100):.0f}%")
        hr4.metric("Model Edge",  f"{abs(res.over_prob-0.5)*200:.0f}%")

        # ── Key factors ────────────────────────────────────────────────────
        st.markdown("**Key Factors**")
        icons = {"pos": "✅", "neg": "⚠️", "neu": "ℹ️"}
        parts = [f"{icons.get(c,'')} {t}" for c, t in res.factors]
        st.markdown("  ·  ".join(parts))

        # ── Add to parlay ──────────────────────────────────────────────────
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
                st.success(f"Added {res.label} · {len(st.session_state.parlay_legs)} legs in parlay")
                st.rerun()
        else:
            st.caption("✅ Already in parlay")
