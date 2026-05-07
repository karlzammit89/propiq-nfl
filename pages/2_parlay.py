"""Page 2 — Parlay Builder with Correlation Engine"""
import streamlit as st
from utils.engine import compute_parlay, get_correlation

st.markdown("## 🎯 Parlay Builder")
st.caption("Add legs from the Prop Generator · Correlation engine flags boosts and conflicts")

legs = st.session_state.parlay_legs

if not legs:
    st.info("👈 Go to **Prop Generator**, generate props, and click **Add to Parlay** on any market.")
    st.stop()

# ── Legs ──────────────────────────────────────────────────────────────────────
st.markdown(f"### {len(legs)} Legs")

for i, leg in enumerate(legs):
    with st.container():
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        with c1:
            st.markdown(f"**{leg['player_name']}**")
            line_str = leg['line_display'] if leg['is_bool'] else f"Over {leg['line_display']}"
            st.caption(f"{leg['market_label']} · {line_str}")
        with c2:
            st.markdown(f"Odds: **{leg['vig_over']}**")
        with c3:
            st.markdown(f"Prob: **{leg['over_prob']*100:.1f}%**")
        with c4:
            if st.button("🗑", key=f"rm_{i}_{leg['key']}"):
                st.session_state.parlay_legs.pop(i)
                st.rerun()

        # Correlation with other legs
        corr_found = []
        for j, other in enumerate(legs):
            if i == j:
                continue
            corr = get_correlation(
                {"player_id": leg["player_id"], "market": leg["market"],
                 "team": leg["team"], "pos": leg["pos"]},
                {"player_id": other["player_id"], "market": other["market"],
                 "team": other["team"], "pos": other["pos"]},
            )
            if corr["value"] != 0:
                icon = "✅" if corr["value"] > 0 else "⚠️"
                corr_found.append(f"{icon} {corr['label']} w/ {other['player_name'].split()[-1]}")
        if corr_found:
            st.caption("  ·  ".join(corr_found))

    st.divider()

# ── Parlay Summary ────────────────────────────────────────────────────────────
summary = compute_parlay(legs)
if not summary:
    st.stop()

st.markdown("### 📊 Parlay Summary")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Legs", summary["legs"])
s2.metric("Combined Odds", summary["payout_american"])
s3.metric("Book Implied %", f"{100/summary['combined_decimal']:.1f}%")
s4.metric("Model True %", f"{summary['adj_prob']*100:.1f}%")

st.markdown(f"### 💰 $100 Payout: **${summary['payout_100']:,}**")

# Correlation alerts
if summary["has_negative_corr"]:
    st.error(
        "⚠️ **Correlation Warning:** One or more legs move against each other (negative correlation). "
        "Your true win probability is lower than the independent estimate. "
        "Consider replacing conflicting legs to strengthen the parlay."
    )
elif summary["has_positive_corr"]:
    st.success(
        "✅ **Correlation Boost Detected:** Your legs have positive correlation — "
        "when one hits, it makes others more likely. Your true probability is higher than independent odds suggest."
    )
else:
    st.info("ℹ️ Legs appear uncorrelated — probability is approximately independent.")

# Correlated pair detail
if summary["corr_pairs"]:
    with st.expander("Correlation pair details"):
        for cp in summary["corr_pairs"]:
            i, j = cp["i"], cp["j"]
            corr = cp["corr"]
            icon = "✅" if corr["value"] > 0 else "⚠️"
            st.markdown(
                f"{icon} **{legs[i]['player_name']}** ({legs[i]['market_label']}) "
                f"+ **{legs[j]['player_name']}** ({legs[j]['market_label']}) "
                f"→ {corr['label']} (val: {corr['value']:+.1f})"
            )

# Clear button
st.markdown("---")
if st.button("🗑 Clear All Legs", use_container_width=False):
    st.session_state.parlay_legs = []
    st.rerun()
