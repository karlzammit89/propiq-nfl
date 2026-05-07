"""
PropIQ v3 — NFL Player Prop Odds Engine
100% Free · No API keys · No quotas · Always current rosters

Data sources:
  ESPN public API  — LIVE rosters, stats, schedules, defense, injuries
  RotoWire scraper — game-day inactives & active/inactive status
  Open-Meteo       — live weather (free, no key)
  PropIQ engine    — statistical projections & fair odds
"""

import streamlit as st

st.set_page_config(
    page_title="PropIQ · NFL Props",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
section[data-testid="stSidebar"] {
    background: #0d1120; border-right: 1px solid rgba(255,255,255,0.07);
}
.main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
div[data-testid="metric-container"] {
    background: #121828; border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px; padding: 14px 18px;
}
h1, h2, h3 { font-family: 'Rajdhani', sans-serif !important; letter-spacing: 0.04em; }
.stButton > button {
    background: #06d6a0; color: #000; font-family: 'Rajdhani', sans-serif;
    font-weight: 700; font-size: 15px; letter-spacing: 0.08em;
    border: none; border-radius: 8px; padding: 10px 24px;
}
.stButton > button:hover { background: #04b887; color: #000; }
.stTabs [data-baseweb="tab-list"] { background: #0d1120; gap: 4px; }
.stTabs [data-baseweb="tab"] {
    background: #121828; border-radius: 6px; color: #8b97ab;
    font-family: 'Rajdhani', sans-serif; font-weight: 600;
    font-size: 14px; letter-spacing: 0.06em;
    border: 1px solid rgba(255,255,255,0.06);
}
.stTabs [aria-selected="true"] {
    background: rgba(6,214,160,0.12) !important;
    color: #06d6a0 !important; border-color: rgba(6,214,160,0.3) !important;
}
.streamlit-expanderHeader {
    background: #121828; border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px; font-family: 'Rajdhani', sans-serif; font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

from utils.state import init_state
init_state()

# ── Live roster — load once, cache 6 hours ────────────────────────────────────
if not st.session_state.get("player_db_loaded"):
    from utils.roster import get_player_db_with_progress
    db = get_player_db_with_progress()
    st.session_state.live_player_db = db
    st.session_state.player_db_loaded = True
    st.session_state.player_db_size = len(db)

# ── Navigation ────────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/1_props.py",    title="Prop Generator",   icon="🏈"),
    st.Page("pages/2_parlay.py",   title="Parlay Builder",   icon="🎯"),
    st.Page("pages/3_injuries.py", title="Injuries & Snaps", icon="🩺"),
    st.Page("pages/4_settings.py", title="Data Sources",     icon="📡"),
])
pg.run()
