"""Page 4 — Data Sources & Settings"""
import streamlit as st
from utils.api import fetch_espn_injuries, fetch_rotowire_inactives

st.markdown("## ⚙️ Data Sources & Settings")
st.caption("PropIQ runs 100% free — no API keys, no quotas, no cost ever")

# ── Live status check ─────────────────────────────────────────────────────────
st.markdown("### 📡 Live Source Status")
st.caption("Checking each source right now…")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.spinner("ESPN…"):
        espn = fetch_espn_injuries()
    if espn:
        st.success(f"✅ ESPN API\n\n{len(espn)} players in injury report")
    else:
        st.warning("⚠️ ESPN API\n\nNo data returned — fallback active")

with col2:
    with st.spinner("RotoWire…"):
        roto = fetch_rotowire_inactives()
    if roto:
        st.success(f"✅ RotoWire\n\n{len(roto)} players flagged")
    else:
        st.info("ℹ️ RotoWire\n\nNo inactives yet (mid-week is normal)")

with col3:
    import requests
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast?latitude=40&longitude=-74&current=temperature_2m", timeout=5)
        r.raise_for_status()
        st.success("✅ Open-Meteo\n\nWeather live")
    except Exception:
        st.warning("⚠️ Open-Meteo\n\nUsing fallback weather")

with col4:
    try:
        r2 = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard", timeout=5)
        r2.raise_for_status()
        st.success("✅ ESPN Scoreboard\n\nSchedule & odds live")
    except Exception:
        st.warning("⚠️ ESPN Scoreboard\n\nUsing fallback schedule")

st.divider()

# ── Source details ────────────────────────────────────────────────────────────
st.markdown("### 🗂️ All Data Sources")
st.markdown("""
| Source | Data provided | Refresh | Cost |
|--------|--------------|---------|------|
| **ESPN public API** | Schedules, matchups, defense rankings, injuries, embedded odds | 15–60 min | Free forever |
| **RotoWire inactives** | Game-day confirmed inactive/active status | 10 min | Free (scraper) |
| **RotoWire lineups** | Projected starters, mid-week status | 10 min | Free (scraper) |
| **Open-Meteo** | Live weather for outdoor stadiums | 30 min | Free forever, no key |
| **PropIQ engine** | Prop projections, fair odds, correlations | Real-time | Free forever |
| **PropIQ fallback** | 2024 season baselines, snap counts | Each deploy | Built-in |

**No API keys needed. No quotas. No credit card. No expiry date.**
""")

st.divider()

# ── Cache controls ────────────────────────────────────────────────────────────
st.markdown("### 🔄 Cache Controls")
st.caption("Data is cached to avoid hitting ESPN/RotoWire too frequently. Clear here if you want a fresh pull.")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🗑 Clear all caches", use_container_width=True):
        st.cache_data.clear()
        st.success("All caches cleared — next page load pulls fresh data.")
with c2:
    if st.button("🔄 Refresh injury data", use_container_width=True):
        fetch_espn_injuries.clear()
        fetch_rotowire_inactives.clear()
        st.success("Injury caches cleared.")
with c3:
    if st.button("🔄 Refresh schedules", use_container_width=True):
        from utils.api import fetch_schedule, fetch_defense_ratings
        fetch_schedule.clear()
        fetch_defense_ratings.clear()
        st.success("Schedule & defense caches cleared.")

st.divider()

# ── Cache TTL reference ───────────────────────────────────────────────────────
st.markdown("### ⏱ Auto-Refresh Schedule")
st.markdown("""
| Data | Cache TTL | Notes |
|------|-----------|-------|
| Live odds / ESPN scoreboard | **2 min** | Fastest refresh |
| RotoWire inactives | **10 min** | Game-day inactives post ~90 min before kickoff |
| ESPN injury report | **15 min** | Aligns with NFL Wed/Thu/Fri/Sat report cycle |
| Schedules & defense stats | **1 hour** | Stable within week; updates after each game |
| Snap counts | **1 hour** | Updates post-game via fallback |
| Weather | **30 min** | Open-Meteo free refresh |

Streamlit's `@st.cache_data(ttl=N)` handles all of this automatically — the app stays current as long as it's running.
""")

st.divider()

# ── Deployment note ───────────────────────────────────────────────────────────
st.markdown("### 🚀 Keeping the App Alive (Streamlit Free Tier)")
st.markdown("""
Streamlit Community Cloud's free tier sleeps apps after **7 days of no visits**.
To keep PropIQ always awake during the NFL season, use a free uptime monitor:

1. Go to [uptimerobot.com](https://uptimerobot.com) and create a free account
2. Click **"Add New Monitor"**
3. Set type to **HTTP(S)**, paste your Streamlit app URL, interval **5 minutes**
4. Click **"Create Monitor"**

UptimeRobot pings your app every 5 minutes for free — Streamlit never sleeps it.
This completely solves the inactivity problem at zero cost.
""")
