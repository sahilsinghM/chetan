"""
ATOS Streamlit Dashboard — entry point.

Run with:
    streamlit run atos/ui/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="ATOS Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
from config.settings import settings

cfg = settings()
mode_badge = "📄 PAPER" if cfg.paper_trade_mode else "💰 LIVE"
mode_color = "green" if cfg.paper_trade_mode else "red"

st.sidebar.title("ATOS")
st.sidebar.markdown(
    f"<span style='background:{mode_color};color:white;padding:2px 8px;"
    f"border-radius:4px;font-size:0.8em'>{mode_badge}</span>",
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

# Navigation
pages = {
    "📊 Dashboard": "atos/ui/pages/01_dashboard.py",
    "📝 Trade Entry": "atos/ui/pages/03_trade_entry.py",
    "📖 Journal": "atos/ui/pages/04_journal.py",
}

selection = st.sidebar.radio("Navigate", list(pages.keys()))
st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0 — Phase 1")

# ── Route to page ──────────────────────────────────────────────────────────────
if selection == "📊 Dashboard":
    from atos.ui.pages import dashboard

    dashboard.render()
elif selection == "📝 Trade Entry":
    from atos.ui.pages import trade_entry

    trade_entry.render()
elif selection == "📖 Journal":
    from atos.ui.pages import journal

    journal.render()
