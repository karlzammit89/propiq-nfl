"""
PropIQ — NFL Player Prop Odds Engine
Full Streamlit app with live API connections.
"""

import streamlit as st

st.set_page_config(
    page_title="PropIQ · NFL Prop Engine",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1120;
    border-right: 1px solid rgba(255,255,255,0.07);
}

/* Main area */
.main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* Metric cards */
div[data-testid="metric-container"] {
    background: #121828;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 14px 18px;
}

/* Headers */
h1, h2, h3 { font-family: 'Rajdhani', sans-serif !important; letter-spacing: 0.04em; }

/* Accent color overrides */
.stButton > button {
    background: #06d6a0;
    color: #000;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 15px;
    letter-spacing: 0.08em;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
}
.stButton > button:hover { background: #04b887; color: #000; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #0d1120; gap: 4px; }
.stTabs [data-baseweb="tab"] {
    background: #121828;
    border-radius: 6px;
    color: #8b97ab;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 0.06em;
    border: 1px solid rgba(255,255,255,0.06);
}
.stTabs [aria-selected="true"] {
    background: rgba(6,214,160,0.12) !important;
    color: #06d6a0 !important;
    border-color: rgba(6,214,160,0.3) !important;
}

/* Selectbox, multiselect */
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #182032;
    border-color: rgba(255,255,255,0.1);
    color: #e8edf5;
}

/* Dataframe */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* Expander */
.streamlit-expanderHeader {
    background: #121828;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 600;
}

/* Badges */
.badge-high { background:#06d6a022; color:#06d6a0; border:1px solid #06d6a044; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-med  { background:#ffd16622; color:#ffd166; border:1px solid #ffd16644; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-low  { background:#ef476f22; color:#ef476f; border:1px solid #ef476f44; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-inj-q { background:#ffd16622; color:#ffd166; border:1px solid #ffd16644; padding:1px 7px; border-radius:4px; font-size:10px; font-weight:700; }
.badge-inj-d { background:#ef476f22; color:#ef476f; border:1px solid #ef476f44; padding:1px 7px; border-radius:4px; font-size:10px; font-weight:700; }
.badge-inj-o { background:#ef476f44; color:#ef476f; border:1px solid #ef476f66; padding:1px 7px; border-radius:4px; font-size:10px; font-weight:700; }

/* Cards */
.prop-card {
    background: #121828;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
}
.hero-card {
    background: #121828;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 18px;
}
.book-box {
    background: #182032;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
}
.book-best {
    border-color: rgba(6,214,160,0.4);
    background: rgba(6,214,160,0.06);
}
.factor-pos { color:#06d6a0; }
.factor-neg { color:#ef476f; }
.factor-neu { color:#8b97ab; }

/* Odds display */
.odds-over  { font-family:'Rajdhani',sans-serif; font-size:22px; font-weight:700; color:#06d6a0; }
.odds-under { font-family:'Rajdhani',sans-serif; font-size:22px; font-weight:700; color:#ef476f; }
.odds-proj  { font-family:'Rajdhani',sans-serif; font-size:22px; font-weight:700; color:#e8edf5; }

/* Dividers */
hr { border-color: rgba(255,255,255,0.07); }
</style>
""", unsafe_allow_html=True)

# ── Navigation ────────────────────────────────────────────────────────────────
from utils.state import init_state
init_state()

pg = st.navigation([
    st.Page("pages/1_props.py",    title="Prop Generator",    icon="🏈"),
    st.Page("pages/2_parlay.py",   title="Parlay Builder",    icon="🎯"),
    st.Page("pages/3_injuries.py", title="Injuries & Snaps",  icon="🩺"),
    st.Page("pages/4_settings.py", title="API Settings",      icon="⚙️"),
])

pg.run()
