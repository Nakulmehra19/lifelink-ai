"""
AI Assistant page — conversational interface powered by Gemini 2.5 Flash.
"""
import streamlit as st
from ai_engine import get_ai_client, ask_ai

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🤖 LifeLink AI Assistant")
st.caption(
    "Ask anything about blood donation, organ compatibility, the matching process, "
    "eligibility criteria, or how to use this platform. Powered by **Gemini 2.5 Flash**."
)
st.divider()

# ── API key gate ──────────────────────────────────────────────────────────────
api_key = st.session_state.get("gemini_api_key", "")
if not api_key:
    with st.container(border=True):
        st.warning(
            "⚠️ **Gemini API key not configured.**\n\n"
            "Go to **⚙️ Settings** in the sidebar to add your free Gemini API key "
            "and unlock all AI features."
        )
        if st.button("⚙️ Go to Settings", type="primary"):
            st.session_state.current_page = "⚙️  Settings"
            st.session_state._nav_request = "⚙️  Settings"
            st.rerun()
    st.stop()

# ── Suggested prompts (only when conversation is empty) ───────────────────────
if not st.session_state.chat_history:
    with st.container(border=True):
        st.subheader("💡 Suggested Questions")
        st.caption("Click any question to get started, or type your own below.")
        suggestions = [
            "What blood types are compatible with O−?",
            "Can I donate a kidney while still alive?",
            "How does organ matching work in India?",
            "What is the difference between blood and plasma donation?",
            "How can I find a bone marrow donor?",
            "What happens after I confirm a donor match?",
            "Why is O− called the universal donor?",
            "What organs can be donated after brain death?",
        ]
        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                    st.session_state._pending_prompt = suggestion
                    st.rerun()

# ── Handle suggested-prompt clicks ───────────────────────────────────────────
if "_pending_prompt" in st.session_state:
    prompt = st.session_state.pop("_pending_prompt")
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("LifeLink AI is thinking..."):
            try:
                client = get_ai_client(api_key)
                reply  = ask_ai(client, st.session_state.chat_history, prompt)
            except Exception as e:
                reply = f"⚠️ Error communicating with Gemini: {e}"
        st.markdown(reply)
    st.session_state.chat_history.append({"role": "user",  "text": prompt})
    st.session_state.chat_history.append({"role": "model", "text": reply})
    st.rerun()

# ── Render conversation history ───────────────────────────────────────────────
for turn in st.session_state.chat_history:
    role = "user" if turn["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(turn["text"])

# ── Free-form chat input ──────────────────────────────────────────────────────
user_input = st.chat_input("Ask LifeLink AI anything about donation…")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        with st.spinner("LifeLink AI is thinking..."):
            try:
                client = get_ai_client(api_key)
                reply  = ask_ai(client, st.session_state.chat_history, user_input)
            except Exception as e:
                reply = f"⚠️ Error communicating with Gemini: {e}"
        st.markdown(reply)
    st.session_state.chat_history.append({"role": "user",  "text": user_input})
    st.session_state.chat_history.append({"role": "model", "text": reply})
    st.rerun()

# ── Chat controls ─────────────────────────────────────────────────────────────
if st.session_state.chat_history:
    st.divider()
    ctrl_col1, ctrl_col2 = st.columns([1, 4])
    with ctrl_col1:
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    with ctrl_col2:
        st.caption(f"💬 {len(st.session_state.chat_history) // 2} message(s) in this conversation.")

st.divider()
st.caption(
    "⚕️ LifeLink AI provides general information only. "
    "Always consult a licensed physician for medical decisions. "
    "In emergencies, call **112** or your nearest hospital immediately."
)
