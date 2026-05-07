"""Page 4 — Data Sources & Settings (v3)"""
import streamlit as st
import requests

st.markdown("## ⚙️ Data Sources & Settings")
st.caption("PropIQ v3 — 100% free, no API keys, always live data")

db_size = st.session_state.get("player_db_size", 0)
st.success(
    f"✅ **{db_size} active NFL skill players** loaded live from ESPN. "
    "Rosters auto-refresh every 6 hours — trades, signings, and cuts reflected automatically."
)
st.divider()

st.markdown("### 📡 Live Source Status")
col1, col2, col3, col4 = st.columns(4)
with col1:
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/12/roster", timeout=6)
        r.raise_for_status()
        count = sum(len(g.get("items",[])) for g in r.json().get("athletes",[]))
        st.success(f"✅ ESPN Rosters\nLive · {count} KC players")
    except Exception:
        st.warning("⚠️ ESPN Rosters\nUsing cached data")
with col2:
    try:
        r2 = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries", timeout=6)
        r2.raise_for_status()
        total = sum(len(t.get("injuries",[])) for t in r2.json().get("injuries",[]))
        st.success(f"✅ ESPN Injuries\n{total} players listed")
    except Exception:
        st.warning("⚠️ ESPN Injuries\nFallback active")
with col3:
    from utils.api import fetch_rotowire_inactives
    roto = fetch_rotowire_inactives()
    if roto:
        st.success(f"✅ RotoWire\n{len(roto)} players flagged")
    else:
        st.info("ℹ️ RotoWire\nNo inactives yet (mid-week)")
with col4:
    try:
        r3 = requests.get("https://api.open-meteo.com/v1/forecast?latitude=40&longitude=-74&current=temperature_2m", timeout=5)
        r3.raise_for_status()
        st.success("✅ Open-Meteo\nWeather live")
    except Exception:
        st.warning("⚠️ Open-Meteo\nUsing fallback")

st.divider()
st.markdown("### 🗂️ All Data Sources")
st.markdown("""
| Source | What it provides | Refresh | Cost |
|--------|-----------------|---------|------|
| **ESPN Roster API** | Every active NFL skill player, current team | 6 hours | Free forever |
| **ESPN Stats API** | Season per-game averages, L5 form | 6 hours | Free forever |
| **ESPN Schedule API** | Next opponent, spread, O/U | 1 hour | Free forever |
| **ESPN Defense API** | Yards allowed/game, rankings | 1 hour | Free forever |
| **ESPN Injuries API** | Weekly Q / D / Out designations | 15 min | Free forever |
| **RotoWire Inactives** | Game-day confirmed inactive/active | 10 min | Free (scraper) |
| **RotoWire Lineups** | Projected starters mid-week | 10 min | Free (scraper) |
| **Open-Meteo** | Live game-day weather | 30 min | Free forever |

**$0/month · No keys · No quotas · No expiry.**
""")

st.divider()
st.markdown("### 🔄 Manual Refresh Controls")
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🔄 Force roster reload", use_container_width=True):
        from utils.roster import build_live_player_db
        build_live_player_db.clear()
        st.session_state.player_db_loaded = False
        st.cache_data.clear()
        st.success("Cache cleared — reloading…")
        st.rerun()
with c2:
    if st.button("🗑 Clear all caches", use_container_width=True):
        st.cache_data.clear()
        st.success("All caches cleared.")
with c3:
    if st.button("🔄 Refresh injuries", use_container_width=True):
        from utils.api import fetch_espn_injuries, fetch_rotowire_inactives
        fetch_espn_injuries.clear()
        fetch_rotowire_inactives.clear()
        st.success("Injury caches cleared.")

st.divider()
st.markdown("### 🏈 How Roster Freshness Works")
st.markdown("""
PropIQ pulls all 32 NFL rosters live from ESPN every time the app starts or every 6 hours.
This means player team changes (trades, free agent signings, cuts) are reflected automatically
with no manual updates needed on your end — ever.

**What ESPN updates and when:**

| Data | When ESPN updates |
|------|------------------|
| Rosters | Within hours of any transaction |
| Season stats | Night after each game |
| Injury report | Wed / Thu / Fri / Sat each week |
| Game-day inactives (RotoWire) | ~90 min before kickoff |
""")

st.divider()
st.markdown("### 💡 Keep PropIQ Always Awake (Free)")
st.markdown("""
Streamlit's free tier sleeps apps after 7 days with no visits. Fix in 2 minutes:

1. Go to [uptimerobot.com](https://uptimerobot.com) → free account
2. **Add New Monitor** → type: HTTP(S)
3. Paste your app URL → interval: **5 minutes** → Save

PropIQ will never sleep during the NFL season.
""")
