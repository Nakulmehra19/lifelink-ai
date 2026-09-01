"""
LifeLink — Donor-Recipient Matching Platform
Main entry point: multi-page Streamlit app.
"""
import streamlit as st
from data_store import init_store

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="LifeLink — Donation Matching",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialise session-state store ─────────────────────────────────────────
init_store()

# ── Sidebar navigation ─────────────────────────────────────────────────────
st.sidebar.title("🩸 LifeLink")
st.sidebar.caption("Blood & Organ Donation Platform")
st.sidebar.markdown("---")

PAGES = {
    "🏠 Home":                  "pages/home.py",
    "📋 Register as Donor":     "pages/register_donor.py",
    "🚨 Post Urgent Request":   "pages/post_request.py",
    "🔗 Find Matches":          "pages/find_matches.py",
    "📊 Dashboard":             "pages/dashboard.py",
    "🤖 AI Assistant":          "pages/ai_assistant.py",
    "⚙️  Settings":             "pages/settings.py",
}

# Use radio for page selection stored in session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Home"

selected = st.sidebar.radio(
    "Navigate",
    list(PAGES.keys()),
    index=list(PAGES.keys()).index(st.session_state.current_page),
    label_visibility="collapsed",
)
st.session_state.current_page = selected

# ── Live stats in sidebar ───────────────────────────────────────────────────
st.sidebar.markdown("---")
donors     = st.session_state.get("donors",   [])
requests   = st.session_state.get("requests", [])
matches    = st.session_state.get("matches",  [])
avail      = sum(1 for d in donors  if d["status"] == "Available")
open_reqs  = sum(1 for r in requests if r["status"] == "Open")

col1, col2, col3 = st.sidebar.columns(3)
col1.metric("Donors",   avail)
col2.metric("Requests", open_reqs)
col3.metric("Matched",  len(matches))

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Gemini 3.6 Flash ✨")

# ── Route to selected page ──────────────────────────────────────────────────
with open(PAGES[selected], encoding="utf-8") as _f:
    exec(_f.read(), {"__name__": "__main__"})
