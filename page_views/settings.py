"""
Settings page — Gemini API key configuration and data management.
"""
import streamlit as st
from data_store import clear_donors, clear_requests, clear_matches, reset_all

# ── Page header ───────────────────────────────────────────────────────────────
st.title("⚙️ Settings")
st.caption("Configure your LifeLink platform preferences and API credentials.")
st.divider()

# ── Section 1: Gemini API Key ─────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("🔑 Gemini API Key")
    st.markdown(
        "LifeLink uses **Gemini 2.5 Flash** for AI match explanations and the conversational assistant. "
        "Get your free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)."
    )

    current_key = st.session_state.get("gemini_api_key", "")

    # Status indicator
    if current_key:
        masked = current_key[:6] + "••••••••••••" + current_key[-4:]
        st.success(f"✅ API key active: `{masked}`")
    else:
        st.warning("⚠️ No API key set — AI features are disabled.")

    api_key_input = st.text_input(
        "Enter Gemini API Key",
        value=current_key,
        type="password",
        placeholder="AIza...",
        help="Your key is stored only in session memory and never sent anywhere except Google's API.",
    )

    btn_col1, btn_col2 = st.columns([2, 1])
    with btn_col1:
        if st.button("💾 Save & Verify API Key", type="primary", use_container_width=True):
            if api_key_input.strip():
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
    with btn_col2:
        if st.button("🗑️ Clear API Key", use_container_width=True):
            st.session_state.gemini_api_key = ""
            st.info("API key cleared.")
            st.rerun()

st.divider()

# ── Section 2: Data Management ────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("🗄️ Session Data Management")
    st.caption(
        "All data lives in browser session memory. Refreshing the page resets to seed data. "
        "Use these controls to manage records during your session."
    )

    data_col1, data_col2, data_col3 = st.columns(3)

    with data_col1:
        with st.container(border=True):
            n_donors = len(st.session_state.donors)
            st.metric("Donors in Session", n_donors)
            if st.button("🗑️ Clear All Donors", use_container_width=True):
                clear_donors()
                st.warning("All donors cleared.")
                st.rerun()

    with data_col2:
        with st.container(border=True):
            n_reqs = len(st.session_state.requests)
            st.metric("Requests in Session", n_reqs)
            if st.button("🗑️ Clear All Requests", use_container_width=True):
                clear_requests()
                st.warning("All requests cleared.")
                st.rerun()

    with data_col3:
        with st.container(border=True):
            n_matches = len(st.session_state.matches)
            st.metric("Matches in Session", n_matches)
            if st.button("🗑️ Clear All Matches", use_container_width=True):
                clear_matches()
                st.warning("All matches cleared.")
                st.rerun()

st.divider()

# ── Section 3: Full Reset ─────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("♻️ Full Platform Reset")
    st.caption("Restore the platform to its initial seed state (8 sample donors, 3 sample requests).")

    reset_col, _ = st.columns([2, 3])
    with reset_col:
        if st.button("🔄 Reset All Data to Seed State", type="secondary", use_container_width=True):
            reset_all()
            st.session_state.chat_history = []
            st.success("✅ Platform reset to seed state successfully.")
            st.rerun()

st.divider()

# ── Section 4: About ──────────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("ℹ️ About LifeLink")
    col_info, col_features = st.columns(2)

    with col_info:
        st.info(
            "**LifeLink — Donor-Recipient Matching Platform**\n\n"
            "Version: 1.0.0  \n"
            "AI Model: Gemini 2.5 Flash (google-genai SDK)  \n"
            "Framework: Streamlit 1.62+  \n"
            "Data: In-session only (no external database)  \n"
            "Coverage: 40 Indian cities"
        )

    with col_features:
        st.success(
            "**Features:**\n\n"
            "- Blood and organ donor registration\n"
            "- Urgent request posting with triage urgency\n"
            "- Automatic matching engine (blood-type + location)\n"
            "- AI-powered match explanations\n"
            "- Conversational AI assistant\n"
            "- Live dashboard with analytics"
        )

    st.caption("*Built with ❤️ to save lives. Every donation can save up to 8 people.*")
