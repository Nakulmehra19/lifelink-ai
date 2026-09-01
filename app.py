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

# ── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.title("🩸 LifeLink")
st.sidebar.caption("Blood & Organ Donation Platform")
st.sidebar.divider()

PAGES = {
    "🏠 Home":                  "page_views/home.py",
    "📋 Register as Donor":     "page_views/register_donor.py",
    "🚨 Post Urgent Request":   "page_views/post_request.py",
    "🔗 Find Matches":          "page_views/find_matches.py",
    "📊 Dashboard":             "page_views/dashboard.py",
    "🤖 AI Assistant":          "page_views/ai_assistant.py",
    "⚙️  Settings":             "page_views/settings.py",
}

# Navigation
if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Home"

st.sidebar.caption("NAVIGATION")
selected = st.sidebar.radio(
    "Navigate",
    list(PAGES.keys()),
    index=list(PAGES.keys()).index(st.session_state.current_page),
    label_visibility="collapsed",
)
st.session_state.current_page = selected

# ── Live platform stats ─────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.caption("LIVE STATS")

donors   = st.session_state.get("donors",   [])
requests = st.session_state.get("requests", [])
matches  = st.session_state.get("matches",  [])

avail     = sum(1 for d in donors   if d["status"] == "Available")
open_reqs = sum(1 for r in requests if r["status"] == "Open")
critical  = sum(1 for r in requests if r.get("urgency") == "Critical" and r["status"] == "Open")

col1, col2 = st.sidebar.columns(2)
col1.metric("Donors",    avail)
col2.metric("Requests",  open_reqs)

col3, col4 = st.sidebar.columns(2)
col3.metric("Matched",   len(matches))
col4.metric("Critical",  critical)

# API key status indicator
st.sidebar.divider()
if st.session_state.get("gemini_api_key", ""):
    st.sidebar.success("🤖 AI Active", icon=None)
else:
    st.sidebar.info("⚙️ Add API key in Settings")

st.sidebar.caption("Powered by Gemini 2.5 Flash ✨")

# ── Route to selected page ──────────────────────────────────────────────────
with open(PAGES[selected], encoding="utf-8") as _f:
    exec(_f.read(), {"__name__": "__main__"})
