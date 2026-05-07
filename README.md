# PropIQ — NFL Player Prop Odds Engine

A full Streamlit application for generating NFL player prop odds with:
- **Live odds** from DraftKings, FanDuel, BetMGM, Caesars, PointsBet (via The Odds API)
- **Auto-loaded matchups** — select a player, instantly see their next opponent, stadium, weather, spread, and O/U
- **Live defense ratings** from Sportradar (32-team pass/rush/efficiency rankings)
- **Injury report** pulled from ESPN's public feed + FantasyLife
- **Snap count tracking** with prop impact adjustments
- **Parlay builder** with correlation detection (positive boosts, negative warnings)
- **Statistical engine** — normal distribution probability math, multi-factor modeling

---

## Quick Start

### 1. Install dependencies
```bash
cd propiq
pip install -r requirements.txt
```

### 2. Run without API keys (uses built-in 2024 season data)
```bash
streamlit run app.py
```
The app works fully out of the box with fallback data. All math, projections,
parlay builder, and injury data work — live odds use modelled prices.

### 3. Add API keys for live data (optional but recommended)
Navigate to **⚙️ API Settings** in the sidebar, paste your keys, and click Save.

Or create a `.env` file:
```env
ODDS_API_KEY=your_key_here
SPORTRADAR_KEY=your_key_here
FANTASYLIFE_KEY=your_key_here
```

---

## API Keys — Where to Get Them

| Service | URL | Free Tier |
|---------|-----|-----------|
| **The Odds API** | https://the-odds-api.com | 500 req/month |
| **Sportradar** | https://developer.sportradar.com | 1,000 req/month (trial) |
| **FantasyLife** | https://fantasylife.com | Varies |
| **Open-Meteo** (weather) | https://open-meteo.com | Always free, no key |

The Odds API is the most impactful key — it unlocks real DraftKings/FanDuel/BetMGM lines.

---

## Deployment

### Streamlit Community Cloud (free)
1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Connect your repo, set `app.py` as the entry point
4. Add API keys in **Secrets** (Settings → Secrets):
   ```toml
   ODDS_API_KEY = "your_key"
   SPORTRADAR_KEY = "your_key"
   FANTASYLIFE_KEY = "your_key"
   ```
5. Update `utils/api.py` to read: `import os; key = os.getenv("ODDS_API_KEY", "")`

### Local with persistent keys
```bash
# Create .streamlit/secrets.toml
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
ODDS_API_KEY = "your_key"
SPORTRADAR_KEY = "your_key"
FANTASYLIFE_KEY = "your_key"
EOF

streamlit run app.py
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t propiq .
docker run -p 8501:8501 \
  -e ODDS_API_KEY=your_key \
  -e SPORTRADAR_KEY=your_key \
  propiq
```

---

## Auto-Update Schedule

| Data | Cache TTL | Notes |
|------|-----------|-------|
| Live odds | 2 min | Streamlit cache auto-expires |
| Schedules | 1 hour | Stable within week |
| Defense stats | 1 hour | Updates after each game |
| Injury report | 15 min | Aligns with NFL report cycle |
| Snap counts | 1 hour | Updates post-game |
| Weather | 30 min | Open-Meteo free refresh |

Streamlit's `@st.cache_data(ttl=N)` handles all refreshes automatically —
the app stays current as long as it's running.

---

## Project Structure

```
propiq/
├── app.py                  # Entry point, navigation, CSS
├── requirements.txt
├── pages/
│   ├── 1_props.py          # Prop generator (main page)
│   ├── 2_parlay.py         # Parlay builder + correlation engine
│   ├── 3_injuries.py       # Injury report + snap counts
│   └── 4_settings.py       # API key management
└── utils/
    ├── state.py             # Session state initialization
    ├── api.py               # All API calls (Odds API, Sportradar, ESPN, Open-Meteo)
    ├── engine.py            # Statistical engine (projections, math, correlation)
    ├── player_db.py         # 80+ player stats database
    └── fallback_data.py     # 2024 season fallback schedules/defense/injuries
```

---

## Statistical Model

Each prop projection combines:

1. **Season regression** — per-game baseline average
2. **Defense modifier** — opponent's yards/game vs position relative to league average (215 pass, 108 rush)
3. **Environment modifier** — weather (cold, wind, rain, snow, dome), surface (turf +3% pass)
4. **Home/away** — +4% home, -4% away
5. **Game total** — O/U scales offensive opportunity
6. **L5 form** — recent 5-game trend multiplier
7. **Availability** — snap share × injury status factor (Q=88%, D=65%, O=0%)

Probability is computed via normal CDF against the generated line.
Vig is added at 4.6% to simulate sportsbook pricing.
