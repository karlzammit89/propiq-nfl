"""Shared Streamlit session-state helpers."""
import streamlit as st


def init_state():
    defaults = {
        "parlay_legs": [],
        "last_results": {},
        "api_keys": {
            "odds_api": "",
            "sportradar": "",
            "fantasy_life": "",
        },
        "selected_player": None,
        "selected_markets": ["pass_yds", "pass_tds", "rush_yds", "rec_yds"],
        "refresh_cache": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
