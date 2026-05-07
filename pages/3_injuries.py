"""Page 3 — Injuries & Snap Counts (RotoWire + ESPN, fully free)"""
import streamlit as st
import pandas as pd
from utils.api import fetch_rotowire_inactives, fetch_espn_injuries, fetch_snap_counts
from utils.fallback_data import FALLBACK_SNAPS

st.markdown("## 🩺 Injuries, Inactives & Snap Counts")
st.caption("RotoWire inactives (game-day) · ESPN injury report (weekly) · All free, no keys")

# ── Data source status ────────────────────────────────────────────────────────
with st.expander("📡 Live Data Sources", expanded=False):
    st.markdown("""
| Source | Updates | What it provides |
|--------|---------|-----------------|
| **RotoWire Inactives** | Game day (Sun ~11:30am ET) | Confirmed active / inactive per player |
| **RotoWire Lineups** | Weekly | Projected starters, depth chart flags |
| **ESPN Injuries API** | Wed / Thu / Fri / Sat | Full weekly injury report (Q/D/Out) |
| **PropIQ Fallback** | Each deploy | Season snap share baselines |

RotoWire takes priority on game day. ESPN is used mid-week. All sources are free with no API key.
""")

# ── RotoWire Inactives ────────────────────────────────────────────────────────
st.markdown("### 🔴 RotoWire — Active / Inactive Status")
st.caption("Refreshes every 10 minutes · Most accurate on game day")

with st.spinner("Fetching RotoWire inactives…"):
    roto_data = fetch_rotowire_inactives()

if roto_data:
    roto_rows = []
    for name, info in roto_data.items():
        status = info.get("status", "ACTIVE")
        icon   = {"INACTIVE": "⛔", "QUESTIONABLE": "🟡", "ACTIVE": "✅"}.get(status, "ℹ️")
        impact = {
            "INACTIVE":    "❌ Do not bet — zero output",
            "QUESTIONABLE": "⚠️ ~12% output reduction",
            "ACTIVE":      "✅ Full projection",
        }.get(status, "ℹ️ Monitor")
        roto_rows.append({
            "Player":   name,
            "Team":     info.get("team", "—"),
            "Status":   f"{icon} {status}",
            "Note":     info.get("note", "—"),
            "Impact":   impact,
        })

    # Sort: inactives first, then questionable
    order = {"⛔ INACTIVE": 0, "🟡 QUESTIONABLE": 1, "✅ ACTIVE": 2}
    roto_rows.sort(key=lambda r: order.get(r["Status"], 3))
    st.dataframe(pd.DataFrame(roto_rows), use_container_width=True, hide_index=True)

    inactives  = [r for r in roto_rows if "INACTIVE"     in r["Status"]]
    questionable = [r for r in roto_rows if "QUESTIONABLE" in r["Status"]]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total flagged", len(roto_data))
    col2.metric("⛔ Inactive",    len(inactives))
    col3.metric("🟡 Questionable", len(questionable))
else:
    st.info(
        "RotoWire inactives haven't been posted yet — "
        "they are released ~90 min before kickoff on game days (Sun/Mon/Thu). "
        "ESPN weekly report is shown below."
    )

st.divider()

# ── ESPN Weekly Injury Report ─────────────────────────────────────────────────
st.markdown("### 📋 ESPN — Weekly Injury Report")
st.caption("Covers Q / Doubtful / Out designations · Refreshes every 15 minutes")

with st.spinner("Fetching ESPN injury report…"):
    espn_inj = fetch_espn_injuries()

if espn_inj:
    STATUS_ICON = {"Q": "🟡 Q", "D": "🔴 D", "O": "⛔ OUT", "P": "🟢 Probable", "": "✅ Active"}
    IMPACT_MAP  = {
        "O": "❌ Do not bet",
        "D": "🔴 ~35% downgrade",
        "Q": "🟡 ~12% downgrade",
        "P": "✅ Full projection",
        "":  "✅ Full projection",
    }

    espn_rows = []
    for name, info in espn_inj.items():
        s = info.get("status", "")
        espn_rows.append({
            "Player":    name,
            "Team":      info.get("team", "—"),
            "Status":    STATUS_ICON.get(s, s),
            "Injury":    info.get("note", "—")[:60],
            "Impact":    IMPACT_MAP.get(s, "ℹ️ Monitor"),
        })

    espn_rows.sort(key=lambda r: ("OUT" not in r["Status"], "D" not in r["Status"], "Q" not in r["Status"]))
    st.dataframe(pd.DataFrame(espn_rows), use_container_width=True, hide_index=True)
else:
    st.warning("ESPN injury data unavailable — check your internet connection.")

st.divider()

# ── Snap Count Tracker ────────────────────────────────────────────────────────
st.markdown("### 📊 Snap Count Tracker")
st.caption("Season average snap share · Low snap players receive output reduction in props")

team_filter = st.selectbox(
    "Filter by team",
    ["ALL"] + sorted(FALLBACK_SNAPS.keys()),
)

snap_rows = []
for team, players in FALLBACK_SNAPS.items():
    if team_filter != "ALL" and team != team_filter:
        continue
    for name, snap in players.items():
        flag = (
            "⛔ Very low"  if snap < 0.40 else
            "⚠️ Low"       if snap < 0.60 else
            "🟡 Moderate"  if snap < 0.75 else
            "🟢 High"      if snap < 0.90 else
            "🟢 Full-time"
        )
        snap_rows.append({
            "Player":   name,
            "Team":     team,
            "Snap %":   f"{round(snap * 100)}%",
            "Raw":      snap,
            "Flag":     flag,
        })

snap_df = pd.DataFrame(snap_rows).sort_values("Raw", ascending=False)
st.dataframe(
    snap_df[["Player", "Team", "Snap %", "Flag"]],
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── Reference table ───────────────────────────────────────────────────────────
st.markdown("### How Status Affects PropIQ Projections")
st.markdown("""
| Status | Snap Adj | Output Factor | PropIQ Action |
|--------|----------|--------------|---------------|
| ✅ Active (90%+ snaps) | None | 100% | Full projection |
| 🟡 Questionable | Slight | ~88% | Modest reduction across all markets |
| 🔴 Doubtful | Moderate | ~65% | Significant reduction — use caution |
| ⛔ Inactive / OUT | None | 0% | Props suppressed entirely |
| 📊 Low snap (<65%) | Applied | Scaled | Proportional reduction regardless of injury |

Snap share and injury status multiply together in the engine. A questionable player at 60% snaps
applies `0.88 × 0.75 = 0.66` — a 34% total output reduction across all their prop projections.
""")
