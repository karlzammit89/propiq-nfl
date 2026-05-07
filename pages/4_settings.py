"""Page 4 — API Settings & Documentation"""
import streamlit as st

st.markdown("## ⚙️ API Settings")
st.caption("Configure your API keys for live data. All keys are stored in session only — never saved.")

# ── API Key Inputs ────────────────────────────────────────────────────────────
with st.form("api_form"):
    st.markdown("### 🔑 API Keys")

    st.markdown("**The Odds API** — Live prop odds from DraftKings, FanDuel, BetMGM, Caesars, PointsBet")
    st.markdown("Get your free key at [the-odds-api.com](https://the-odds-api.com) — 500 requests/month free")
    odds_key = st.text_input(
        "Odds API Key",
        value=st.session_state.api_keys.get("odds_api", ""),
        type="password",
        placeholder="Enter your Odds API key...",
    )

    st.divider()

    st.markdown("**Sportradar NFL API** — Live schedules, defense rankings, snap counts")
    st.markdown("Trial access at [developer.sportradar.com](https://developer.sportradar.com) — 1,000 req/month free")
    sr_key = st.text_input(
        "Sportradar API Key",
        value=st.session_state.api_keys.get("sportradar", ""),
        type="password",
        placeholder="Enter your Sportradar API key...",
    )

    st.divider()

    st.markdown("**FantasyLife API** — Injury reports, weekly snap counts, target share data")
    st.markdown("Get access at [fantasylife.com](https://fantasylife.com)")
    fl_key = st.text_input(
        "FantasyLife API Key",
        value=st.session_state.api_keys.get("fantasy_life", ""),
        type="password",
        placeholder="Enter your FantasyLife API key...",
    )

    submitted = st.form_submit_button("💾 Save Keys", use_container_width=True)
    if submitted:
        st.session_state.api_keys = {
            "odds_api":    odds_key,
            "sportradar":  sr_key,
            "fantasy_life": fl_key,
        }
        # Clear caches to force fresh pulls
        st.cache_data.clear()
        st.success("✅ API keys saved. Caches cleared — next generation will pull fresh data.")

# ── Status ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 📡 Data Source Status")

keys = st.session_state.api_keys
statuses = {
    "Odds API (Live Lines)":       "🟢 Connected" if keys.get("odds_api") else "🟡 Using modelled odds",
    "Sportradar (Schedule/Stats)": "🟢 Connected" if keys.get("sportradar") else "🟡 Using 2024 fallback data",
    "FantasyLife (Injuries)":      "🟢 Connected" if keys.get("fantasy_life") else "🟡 Using ESPN public feed + fallback",
    "Open-Meteo (Weather)":        "🟢 Always active — no key required",
}

for source, status in statuses.items():
    st.markdown(f"**{source}:** {status}")

st.divider()

# ── .env instructions ─────────────────────────────────────────────────────────
st.markdown("### 🔧 Production Setup (`.env` file)")
st.markdown("""
For persistent keys across sessions, create a `.env` file in the project root:

```env
ODDS_API_KEY=your_odds_api_key_here
SPORTRADAR_KEY=your_sportradar_key_here
FANTASYLIFE_KEY=your_fantasylife_key_here
```

Then load it in your shell before running:
```bash
export $(cat .env | xargs)
streamlit run app.py
```

Or update `utils/api.py` to use `os.getenv()` for each key.
""")

st.divider()
st.markdown("### 📋 Auto-Update Cadence")
st.markdown("""
| Data Source | Cache TTL | Updates When |
|-------------|-----------|--------------|
| Live Odds (Odds API) | **2 minutes** | Odds move, line changes |
| Schedules (Sportradar) | **1 hour** | Weekly when schedule is set |
| Defense Stats (Sportradar) | **1 hour** | After each game |
| Injury Report | **15 minutes** | NFL releases Wed/Thu/Fri/Sat reports |
| Snap Counts | **1 hour** | After each game day |
| Weather (Open-Meteo) | **30 min** | Automatically every load |

PropIQ uses Streamlit's `@st.cache_data(ttl=...)` to auto-refresh all data
at the cadences above — just keep the app running and it stays current.
""")
