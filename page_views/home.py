"""Home / landing page."""
import streamlit as st
import pandas as pd
from data_store import BLOOD_COMPATIBILITY, ALL_BLOOD_TYPES

# ── Header ────────────────────────────────────────────────────────────────────
col_logo, col_heading = st.columns([1, 6])
with col_logo:
    st.markdown("# 🩸")
with col_heading:
    st.title("LifeLink — Donate Life, Save Lives")
    st.caption("AI-Powered Blood & Organ Donation Matching Platform for India")

st.divider()

# ── Compute stats ─────────────────────────────────────────────────────────────
donors   = st.session_state.donors
requests = st.session_state.requests
matches  = st.session_state.matches

available = sum(1 for d in donors   if d["status"] == "Available")
pledged   = sum(1 for d in donors   if d["status"] == "Pledged")
open_r    = sum(1 for r in requests if r["status"] == "Open")
matched_r = sum(1 for r in requests if r["status"] == "Matched")
critical  = sum(1 for r in requests if r.get("urgency") == "Critical" and r["status"] == "Open")

# ── Platform KPIs ─────────────────────────────────────────────────────────────
st.subheader("📊 Platform Overview")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🟢 Available Donors",  available)
c2.metric("🤝 Pledged Donors",    pledged)
c3.metric("📋 Open Requests",     open_r)
c4.metric("✅ Matched",           matched_r)
c5.metric(
    "🔴 Critical Cases",
    critical,
    delta="Needs attention" if critical else "All clear",
    delta_color="inverse" if critical else "normal",
)

st.divider()

# ── Alert banners ─────────────────────────────────────────────────────────────
if critical:
    critical_list = [
        r for r in requests
        if r.get("urgency") == "Critical" and r["status"] == "Open"
    ]
    names = ", ".join(r["patient_name"] for r in critical_list)
    st.error(
        f"🔴 **{critical} Critical Case(s) Need Immediate Help:** {names}  \n"
        "Go to **🔗 Find Matches** to connect donors with these patients right now."
    )

if not st.session_state.get("gemini_api_key", ""):
    st.warning(
        "🤖 **AI features are disabled.** Add your Gemini API key in **⚙️ Settings** "
        "to unlock AI match explanations and the conversational assistant."
    )

# ── Quick Actions ─────────────────────────────────────────────────────────────
st.subheader("⚡ Quick Actions")
st.caption("Jump straight into the most common tasks")

qa1, qa2, qa3, qa4 = st.columns(4)

with qa1:
    with st.container(border=True):
        st.markdown("### 📋 Register as Donor")
        st.caption("Join our network of life-savers. Your registration can save up to **8 lives**.")
        if st.button("Register Now →", key="qa_register", use_container_width=True, type="primary"):
            st.session_state.current_page = "📋 Register as Donor"
            st.rerun()

with qa2:
    with st.container(border=True):
        st.markdown("### 🚨 Post a Request")
        st.caption("Patient in need? Post an urgent request and let our AI find compatible donors.")
        if st.button("Post Request →", key="qa_request", use_container_width=True, type="primary"):
            st.session_state.current_page = "🚨 Post Urgent Request"
            st.rerun()

with qa3:
    with st.container(border=True):
        st.markdown("### 🔗 Find Matches")
        st.caption("Browse open requests and instantly match donors by blood type and location.")
        if st.button("Find Matches →", key="qa_match", use_container_width=True, type="primary"):
            st.session_state.current_page = "🔗 Find Matches"
            st.rerun()

with qa4:
    with st.container(border=True):
        st.markdown("### 🤖 AI Assistant")
        st.caption("Ask LifeLink AI about blood types, organ donation, eligibility, and more.")
        if st.button("Ask AI →", key="qa_ai", use_container_width=True, type="primary"):
            st.session_state.current_page = "🤖 AI Assistant"
            st.rerun()

st.divider()

# ── Recent Activity + Compatibility Reference ─────────────────────────────────
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("📰 Recent Activity")
    activity_tab1, activity_tab2 = st.tabs(["🟢 Latest Donors", "📋 Latest Requests"])

    with activity_tab1:
        if donors:
            recent_donors = sorted(donors, key=lambda d: d["registered_at"], reverse=True)[:6]
            for d in recent_donors:
                badge = "🟢" if d["status"] == "Available" else "🤝"
                with st.container(border=True):
                    dc1, dc2 = st.columns([3, 1])
                    with dc1:
                        st.markdown(f"**{badge} {d['name']}**")
                        st.caption(f"{d['blood_type']} · {d['city']} · {d['donation_type']}")
                    with dc2:
                        st.caption(d["status"])
        else:
            st.info("No donors registered yet.")

    with activity_tab2:
        if requests:
            recent_reqs = sorted(requests, key=lambda r: r["posted_at"], reverse=True)[:6]
            for r in recent_reqs:
                icon = {"Critical": "🔴", "High": "🟠", "Moderate": "🟡"}.get(r["urgency"], "⚪")
                border = True
                with st.container(border=border):
                    rc1, rc2 = st.columns([3, 1])
                    with rc1:
                        st.markdown(f"**{icon} {r['patient_name']}**")
                        st.caption(f"{r['blood_type']} · {r['city']} · {r['urgency']}")
                    with rc2:
                        st.caption(r["status"])
        else:
            st.info("No requests posted yet.")

with right_col:
    st.subheader("🩸 Blood Type Compatibility")
    st.caption("Recipient blood type → compatible donor blood types")
    compat_data = []
    for bt in ALL_BLOOD_TYPES:
        compatible = BLOOD_COMPATIBILITY.get(bt, [bt])
        compat_data.append({
            "Recipient": bt,
            "Compatible Donors": "  ·  ".join(compatible),
            "# Types": len(compatible),
        })
    df = pd.DataFrame(compat_data)
    st.dataframe(df, use_container_width=True, hide_index=True, height=310)

    st.divider()
    with st.expander("💡 Key Blood Type Facts"):
        st.info(
            "**O−** is the universal blood donor — compatible with all recipients.\n\n"
            "**AB+** can receive blood from any type.\n\n"
            "**AB+** is the universal plasma donor.\n\n"
            "Only **7%** of people worldwide are O−."
        )

st.divider()
st.caption("LifeLink © 2025 · Powered by Gemini 2.5 Flash · Every donation can save up to 8 lives 💙")
