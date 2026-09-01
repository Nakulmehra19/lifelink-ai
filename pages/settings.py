"""
Settings page — Gemini API key configuration and data management.
"""
import streamlit as st

st.title("⚙️ Settings")
st.markdown("Configure your LifeLink platform preferences and API credentials.")
st.markdown("---")

# ── Gemini API Key ────────────────────────────────────────────────────────────
st.subheader("🔑 Gemini API Key")
st.markdown(
    "LifeLink uses **Gemini 2.0 Flash** for AI match explanations and the conversational assistant. "
    "Get your free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)."
)

current_key = st.session_state.get("gemini_api_key", "")
api_key_input = st.text_input(
    "Gemini API Key",
    value=current_key,
    type="password",
    placeholder="AIza...",
    help="Your key is stored only in session memory and never sent anywhere except Google's API.",
)

col1, col2 = st.columns(2)
with col1:
    if st.button("💾 Save API Key", type="primary", use_container_width=True):
        if api_key_input.strip():
            # Quick validation by attempting a lightweight model call
            with st.spinner("Validating API key with Gemini..."):
                try:
                    from ai_engine import get_ai_client, ask_ai
                    client = get_ai_client(api_key_input.strip())
                    _ = ask_ai(client, [], "Respond with exactly two words: 'API verified'.")
                    st.session_state.gemini_api_key = api_key_input.strip()
                    st.success("✅ API key saved and verified successfully!")
                except Exception as e:
                    st.error(f"❌ API key validation failed: {e}")
        else:
            st.warning("Please enter an API key before saving.")

with col2:
    if st.button("🗑️ Clear API Key", use_container_width=True):
        st.session_state.gemini_api_key = ""
        st.info("API key cleared.")
        st.rerun()

if current_key:
    masked = current_key[:6] + "••••••••••••" + current_key[-4:]
    st.success(f"✅ API key configured: `{masked}`")
else:
    st.warning("⚠️ No API key set — AI features are disabled.")

st.markdown("---")

# ── Data management ───────────────────────────────────────────────────────────
st.subheader("🗄️ Data Management")
st.markdown(
    "All data lives in browser session memory. Refreshing the page resets to seed data. "
    "Use these controls to manage records during your session."
)

data_col1, data_col2, data_col3 = st.columns(3)

with data_col1:
    n_donors = len(st.session_state.donors)
    st.metric("Donors in Session",   n_donors)
    if st.button("🗑️ Clear All Donors", use_container_width=True):
        st.session_state.donors = []
        st.warning("All donors cleared.")
        st.rerun()

with data_col2:
    n_reqs = len(st.session_state.requests)
    st.metric("Requests in Session", n_reqs)
    if st.button("🗑️ Clear All Requests", use_container_width=True):
        st.session_state.requests = []
        st.warning("All requests cleared.")
        st.rerun()

with data_col3:
    n_matches = len(st.session_state.matches)
    st.metric("Matches in Session",  n_matches)
    if st.button("🗑️ Clear All Matches", use_container_width=True):
        st.session_state.matches = []
        st.warning("All matches cleared.")
        st.rerun()

st.markdown("---")

# ── Full reset ────────────────────────────────────────────────────────────────
st.subheader("♻️ Full Reset")
st.markdown("Restore the platform to its initial seed state (8 sample donors, 3 sample requests).")

if st.button("🔄 Reset All Data to Seed State", type="secondary", use_container_width=False):
    from data_store import _seed_donors, _seed_requests
    st.session_state.donors   = _seed_donors()
    st.session_state.requests = _seed_requests()
    st.session_state.matches  = []
    st.session_state.chat_history = []
    st.success("✅ Platform reset to seed state successfully.")
    st.rerun()

st.markdown("---")

# ── About ────────────────────────────────────────────────────────────────────
st.subheader("ℹ️ About LifeLink")
st.info(
    """
    **LifeLink — Donor-Recipient Matching Platform**

    Version: 1.0.0  
    AI Model: Gemini 2.0 Flash (google-genai SDK)  
    Framework: Streamlit 1.62+  
    Data: In-session only (no external database)

    **Features:**
    - Blood and organ donor registration with eligibility checks
    - Urgent request posting with triage urgency levels
    - Automatic matching engine (blood-type + location scoring)
    - AI-powered match explanations and conversational assistant
    - Live dashboard with analytics and charts
    - 40 Indian cities supported

    *Built with ❤️ to save lives. Every donation can save up to 8 people.*
    """
)
