"""Home / landing page."""
import streamlit as st
from data_store import (
    BLOOD_COMPATIBILITY, ALL_BLOOD_TYPES, ORGAN_TYPES, DONATION_TYPES
)

st.title("🩸 LifeLink — Donate Life, Save Lives")
st.markdown(
    """
    > *Every 2 seconds someone in India needs blood. Over 500,000 people die annually
    > awaiting organ transplants. LifeLink bridges donors and recipients instantly.*
    """
)

st.markdown("---")

# ── Hero metrics ────────────────────────────────────────────────────────────
donors    = st.session_state.donors
requests  = st.session_state.requests
matches   = st.session_state.matches

available = sum(1 for d in donors  if d["status"] == "Available")
pledged   = sum(1 for d in donors  if d["status"] == "Pledged")
open_r    = sum(1 for r in requests if r["status"] == "Open")
matched_r = sum(1 for r in requests if r["status"] == "Matched")
critical  = sum(1 for r in requests if r.get("urgency") == "Critical" and r["status"] == "Open")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🟢 Available Donors",   available)
c2.metric("🤝 Pledged Donors",     pledged)
c3.metric("🔴 Open Requests",      open_r)
c4.metric("✅ Matched Requests",   matched_r)
c5.metric("⚠️ Critical Cases",     critical, delta="Needs attention" if critical else None, delta_color="inverse")

st.markdown("---")

# ── Quick actions ────────────────────────────────────────────────────────────
st.subheader("Quick Actions")
qa1, qa2, qa3, qa4 = st.columns(4)

with qa1:
    st.info("**📋 Register as Donor**\n\nJoin our network and save lives by registering as a blood or organ donor.")
    if st.button("Register Now", key="qa_register", use_container_width=True):
        st.session_state.current_page = "📋 Register as Donor"
        st.rerun()

with qa2:
    st.error("**🚨 Post Urgent Request**\n\nPatient in need? Post a request and let our AI find compatible donors instantly.")
    if st.button("Post Request", key="qa_request", use_container_width=True):
        st.session_state.current_page = "🚨 Post Urgent Request"
        st.rerun()

with qa3:
    st.success("**🔗 Find Matches**\n\nBrowse open requests and auto-match donors using blood type and location.")
    if st.button("Find Matches", key="qa_match", use_container_width=True):
        st.session_state.current_page = "🔗 Find Matches"
        st.rerun()

with qa4:
    st.warning("**🤖 AI Assistant**\n\nAsk LifeLink AI anything about blood types, organ donation, and compatibility.")
    if st.button("Ask AI", key="qa_ai", use_container_width=True):
        st.session_state.current_page = "🤖 AI Assistant"
        st.rerun()

st.markdown("---")

# ── Blood type compatibility table ──────────────────────────────────────────
st.subheader("🩸 Blood Type Compatibility Reference")
st.caption("Recipient blood type → compatible donor blood types")

compat_data = []
for bt in ALL_BLOOD_TYPES:
    compatible = BLOOD_COMPATIBILITY.get(bt, [bt])
    compat_data.append({
        "Recipient Blood Type": bt,
        "Compatible Donor Types": "  ·  ".join(compatible),
        "# Compatible Types": len(compatible),
    })

import pandas as pd
df = pd.DataFrame(compat_data)
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Recent activity ──────────────────────────────────────────────────────────
st.subheader("📰 Recent Activity")
left, right = st.columns(2)

with left:
    st.markdown("**Latest Donor Registrations**")
    if donors:
        recent_donors = sorted(donors, key=lambda d: d["registered_at"], reverse=True)[:5]
        for d in recent_donors:
            badge = "🟢" if d["status"] == "Available" else "🤝"
            st.markdown(
                f"{badge} **{d['name']}** — {d['blood_type']} | {d['city']} | {d['donation_type']}"
            )
    else:
        st.caption("No donors registered yet.")

with right:
    st.markdown("**Latest Requests**")
    if requests:
        recent_reqs = sorted(requests, key=lambda r: r["posted_at"], reverse=True)[:5]
        for r in recent_reqs:
            urgency_icon = {"Critical": "🔴", "High": "🟠", "Moderate": "🟡"}.get(r["urgency"], "⚪")
            st.markdown(
                f"{urgency_icon} **{r['patient_name']}** — {r['blood_type']} | {r['city']} | {r['urgency']}"
            )
    else:
        st.caption("No requests posted yet.")

st.markdown("---")
st.caption("LifeLink © 2025 | Powered by Gemini 2.5 Flash | Every donation can save up to 8 lives 💙")
