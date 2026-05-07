"""Page 3 — Injury Report & Snap Counts"""
import streamlit as st
import pandas as pd
from utils.api import fetch_injury_report
from utils.fallback_data import FALLBACK_INJURIES, FALLBACK_SNAPS
from utils.player_db import PLAYER_DB

st.markdown("## 🩺 Injury Report & Snap Counts")
st.caption("Live injury report · weekly snap share · prop impact assessment")

keys = st.session_state.api_keys

with st.spinner("Fetching injury report..."):
    injuries = fetch_injury_report(keys["fantasy_life"])

# ── Injury Report Table ───────────────────────────────────────────────────────
st.markdown("### Active Injury Report")

STATUS_ICONS = {"Q": "🟡 Q", "D": "🔴 D", "O": "⛔ OUT", "IR": "🚫 IR"}
IMPACT_MAP   = {
    "O":  ("⛔ Zero props", "red"),
    "IR": ("⛔ Zero props", "red"),
    "D":  ("🔴 ~35% downgrade", "orange"),
    "Q":  ("🟡 ~12% downgrade", "yellow"),
}

rows = []
for name, info in injuries.items():
    status = info.get("status", "")
    note   = info.get("note", "—")
    team   = info.get("team", "—")
    icon   = STATUS_ICONS.get(status, status)
    impact, _ = IMPACT_MAP.get(status, ("ℹ️ Monitor", "gray"))

    # Look up snap pct from fallback
    snap_pct = None
    snaps = FALLBACK_SNAPS.get(team, {})
    snap_pct = snaps.get(name, None)
    snap_str = f"{round(snap_pct*100)}%" if snap_pct is not None else "N/A"

    rows.append({
        "Player":      name,
        "Team":        team,
        "Status":      icon,
        "Injury":      note,
        "Snap Share":  snap_str,
        "Prop Impact": impact,
    })

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No injuries found in the live feed. Showing fallback data.")
    rows = []
    for name, info in FALLBACK_INJURIES.items():
        status = info.get("status", "")
        note   = info.get("note", "—")
        team   = info.get("team", "—")
        icon   = STATUS_ICONS.get(status, status)
        impact, _ = IMPACT_MAP.get(status, ("ℹ️ Monitor", "gray"))
        rows.append({"Player": name, "Team": team, "Status": icon,
                     "Injury": note, "Prop Impact": impact})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()

# ── Snap Count Tracker ────────────────────────────────────────────────────────
st.markdown("### Snap Count Tracker")
st.caption("Players with notable snap share changes (below 70% or above 90%)")

snap_rows = []
for team, players in FALLBACK_SNAPS.items():
    for name, snap in players.items():
        flag = ""
        if snap < 0.55:
            flag = "⚠️ Low snaps"
        elif snap < 0.70:
            flag = "🟡 Moderate"
        elif snap >= 0.92:
            flag = "🟢 Full-time"
        snap_rows.append({
            "Player":     name,
            "Team":       team,
            "Snap %":     f"{round(snap*100)}%",
            "Snap Share": snap,
            "Flag":       flag,
        })

snap_df = pd.DataFrame(snap_rows)
snap_df = snap_df.sort_values("Snap Share", ascending=False)

# Filter options
filter_opt = st.selectbox("Filter", ["All players", "Low snaps (<70%)", "Full-time (≥90%)"])
if filter_opt == "Low snaps (<70%)":
    snap_df = snap_df[snap_df["Snap Share"] < 0.70]
elif filter_opt == "Full-time (≥90%)":
    snap_df = snap_df[snap_df["Snap Share"] >= 0.90]

st.dataframe(
    snap_df[["Player", "Team", "Snap %", "Flag"]],
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.markdown("### How Injury Status Affects Props")
st.markdown("""
| Status | Output Adjustment | Notes |
|--------|------------------|-------|
| ✅ Active | 100% | Full projection |
| 🟡 Questionable | ~88% | Slight usage/efficiency reduction |
| 🔴 Doubtful | ~65% | Significant snap / target share concern |
| ⛔ OUT / IR | 0% | Do not bet — no projection |

Snap share below 65% applies an additional scaling factor regardless of injury status.
The model adjusts all projections, lines, and probabilities automatically.
""")
