"""
Find Matches page — automatic donor-recipient matching engine.
Uses blood-type compatibility + location scoring.
Optionally explains matches using Gemini AI.
"""
import streamlit as st
import pandas as pd
from data_store import find_matches, record_match, BLOOD_COMPATIBILITY


def _urgency_badge(level: str) -> str:
    return {"Critical": "🔴 Critical", "High": "🟠 High", "Moderate": "🟡 Moderate"}.get(level, level)


# ── Page header ───────────────────────────────────────────────────────────────
st.title("🔗 Find Donor Matches")
st.caption(
    "Select an open request to instantly find compatible donors ranked by "
    "blood-type compatibility and proximity."
)
st.divider()

# ── Summary KPIs ──────────────────────────────────────────────────────────────
# Only approved requests appear in the public matching view
open_requests = [
    r for r in st.session_state.requests
    if r["status"] == "Open" and r.get("verification_status", "Approved") == "Approved"
]
all_requests  = st.session_state.requests
critical_open = [r for r in open_requests if r.get("urgency") == "Critical"]

# Pending-verification notice for the submitting user
my_pending = [
    r for r in st.session_state.requests
    if r.get("verification_status") == "Pending"
]
if my_pending:
    st.info(
        f"🟡 **{len(my_pending)} request(s) are awaiting admin approval** and not yet visible here. "
        "An admin must approve them before matching can begin."
    )

k1, k2, k3, k4 = st.columns(4)
k1.metric("📋 Open Requests",    len(open_requests))
k2.metric("🔴 Critical",         len(critical_open))
k3.metric("✅ Matched",          sum(1 for r in all_requests if r["status"] == "Matched"))
k4.metric("🟢 Available Donors", sum(1 for d in st.session_state.donors if d["status"] == "Available"))

if critical_open:
    st.error(
        f"🔴 **{len(critical_open)} Critical Request(s) Need Immediate Attention!** "
        "Expand the red entries below to find and confirm donors."
    )

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔴 Open Requests", "📋 All Requests History"])

with tab1:
    if not open_requests:
        st.success("🎉 No open requests right now — all requests have been matched!")
    else:
        sorted_requests = sorted(
            open_requests,
            key=lambda r: ["Critical", "High", "Moderate"].index(r["urgency"])
        )
        for req in sorted_requests:
            urgency_icon = {"Critical": "🔴", "High": "🟠", "Moderate": "🟡"}.get(req["urgency"], "⚪")
            label = (
                f"{urgency_icon} {req['urgency'].upper()}  ·  "
                f"{req['patient_name']}  ·  "
                f"{req['blood_type']}  ·  "
                f"{req['hospital']}, {req['city']}"
            )
            with st.expander(label, expanded=(req.get("urgency") == "Critical")):
                # ── Request summary ───────────────────────────────────────
                info_col, meta_col = st.columns([3, 2])

                with info_col:
                    with st.container(border=True):
                        st.markdown(f"**Patient:** {req['patient_name']}")
                        st.markdown(f"**Hospital:** {req['hospital']}, {req['city']}")
                        st.markdown(f"**Blood Type Needed:** `{req['blood_type']}`")
                        st.markdown(f"**Requirement:** {req['donation_type']}")
                        if req.get("organs"):
                            st.markdown(f"**Organs Needed:** {', '.join(req['organs'])}")
                        if req.get("additional_info"):
                            st.markdown(f"**Notes:** {req['additional_info']}")
                        st.caption(f"Request ID: `{req['id']}`  ·  Posted: {req['posted_at']}")

                with meta_col:
                    with st.container(border=True):
                        if req["urgency"] == "Critical":
                            st.error(f"🔴 **CRITICAL CASE**")
                        elif req["urgency"] == "High":
                            st.warning(f"🟠 **High Urgency**")
                        else:
                            st.info(f"🟡 **Moderate**")

                        st.markdown("**Compatible Blood Types:**")
                        compatible_blood = BLOOD_COMPATIBILITY.get(req['blood_type'], [])
                        st.markdown("  ·  ".join(f"`{b}`" for b in compatible_blood))

                st.divider()

                # ── Compatible Donors ─────────────────────────────────────
                st.subheader("🔍 Compatible Donors")
                matches = find_matches(req)

                if not matches:
                    st.warning(
                        "⚠️ No compatible donors found in the current registry. "
                        "Consider sharing on social networks or expanding the search."
                    )
                else:
                    st.success(f"✅ **{len(matches)} compatible donor(s) found** — ranked by compatibility and proximity.")

                    for i, donor in enumerate(matches):
                        same_city   = donor["city"] == req["city"]
                        exact_blood = donor["blood_type"] == req["blood_type"]
                        city_badge  = "📍 Same city" if same_city else f"🗺️ {donor['city']}"
                        blood_badge = "✅ Exact match" if exact_blood else "🔄 Compatible"

                        with st.container(border=True):
                            d_col1, d_col2, d_col3 = st.columns([3, 2, 2])

                            with d_col1:
                                rank_icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
                                st.markdown(f"**{rank_icon} {donor['name']}**")
                                st.caption(
                                    f"🩸 {donor['blood_type']} {blood_badge}  ·  {city_badge}  ·  "
                                    f"Donates: {donor['donation_type']}"
                                    + (f"  ·  Organs: {', '.join(donor.get('organs', []))}" if donor.get("organs") else "")
                                )

                            with d_col2:
                                st.markdown(f"📞 `{donor['phone']}`")
                                st.caption(f"Age {donor['age']}  ·  Status: **{donor['status']}**")

                            with d_col3:
                                if donor["status"] == "Available":
                                    if st.button(
                                        "🤝 Confirm Match",
                                        key=f"match_{req['id']}_{donor['id']}",
                                        use_container_width=True,
                                        type="primary",
                                    ):
                                        record_match(req["id"], donor["id"])
                                        st.success(
                                            f"✅ **Matched!** {donor['name']} → {req['patient_name']}  \n"
                                            "Both parties should be contacted immediately."
                                        )
                                        st.rerun()
                                else:
                                    st.caption(f"Status: {donor['status']}")

                # ── AI explanation ────────────────────────────────────────
                st.divider()
                api_key = st.session_state.get("gemini_api_key", "")
                if api_key:
                    if st.button(
                        "🤖 Explain this match with AI",
                        key=f"ai_explain_{req['id']}",
                        use_container_width=True,
                    ):
                        from ai_engine import get_ai_client, build_match_summary_prompt, ask_ai
                        try:
                            with st.spinner("Analysing compatibility with Gemini 2.5 Flash..."):
                                client  = get_ai_client(api_key)
                                prompt  = build_match_summary_prompt(req, matches)
                                explanation = ask_ai(client, [], prompt)
                            with st.container(border=True):
                                st.markdown("**🤖 AI Analysis**")
                                st.info(explanation)
                        except Exception as e:
                            st.error(f"AI error: {e}")
                else:
                    st.caption("💡 Add your Gemini API key in ⚙️ Settings to enable AI match explanations.")

with tab2:
    if all_requests:
        df = pd.DataFrame(all_requests)
        cols = ["id", "patient_name", "blood_type", "city", "donation_type",
                "urgency", "hospital", "status", "posted_at"]
        df = df[cols]
        df.columns = ["ID", "Patient", "Blood Type", "City", "Type", "Urgency", "Hospital", "Status", "Posted At"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No requests in the system yet.")

# ── Confirmed Matches log ─────────────────────────────────────────────────────
st.divider()
st.subheader("🤝 Confirmed Matches")

if st.session_state.matches:
    matches_log = []
    donor_map  = {d["id"]: d for d in st.session_state.donors}
    req_map    = {r["id"]: r for r in st.session_state.requests}

    for m in st.session_state.matches:
        d = donor_map.get(m["donor_id"], {})
        r = req_map.get(m["req_id"],   {})
        matches_log.append({
            "Match Time": m["matched_at"],
            "Patient":    r.get("patient_name", m["req_id"]),
            "Donor":      d.get("name",  m["donor_id"]),
            "Blood Type": d.get("blood_type", "—"),
            "City":       r.get("city", "—"),
            "Hospital":   r.get("hospital", "—"),
        })

    st.dataframe(pd.DataFrame(matches_log), use_container_width=True, hide_index=True)
else:
    st.info("No matches confirmed yet. Find an open request above to start matching.")
