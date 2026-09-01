"""
Find Matches page — automatic donor-recipient matching engine.
Uses blood-type compatibility + location scoring.
Optionally explains matches using Gemini AI.
"""
import streamlit as st
from data_store import find_matches, record_match, BLOOD_COMPATIBILITY


def _urgency_badge(level: str) -> str:
    return {"Critical": "🔴 Critical", "High": "🟠 High", "Moderate": "🟡 Moderate"}.get(level, level)


st.title("🔗 Find Donor Matches")
st.markdown(
    "Select an open request below to instantly find compatible donors ranked by "
    "blood-type compatibility and proximity."
)
st.markdown("---")

# ── Filter open requests ────────────────────────────────────────────────────
open_requests = [r for r in st.session_state.requests if r["status"] == "Open"]
all_requests  = st.session_state.requests

tab1, tab2 = st.tabs(["🔴 Open Requests", "✅ All Requests"])

with tab1:
    if not open_requests:
        st.info("🎉 No open requests right now — all requests have been matched!")
    else:
        for req in sorted(open_requests, key=lambda r: ["Critical","High","Moderate"].index(r["urgency"])):
            with st.expander(
                f"{_urgency_badge(req['urgency'])} — {req['patient_name']} "
                f"| {req['blood_type']} | {req['city']} | {req['hospital']}"
            ):
                info_col, action_col = st.columns([2, 1])

                with info_col:
                    st.markdown(f"**Request ID:** `{req['id']}`")
                    st.markdown(f"**Patient:** {req['patient_name']}")
                    st.markdown(f"**Blood Type Needed:** {req['blood_type']}")
                    st.markdown(f"**Requirement:** {req['donation_type']}")
                    if req.get("organs"):
                        st.markdown(f"**Organs Needed:** {', '.join(req['organs'])}")
                    st.markdown(f"**Hospital:** {req['hospital']}, {req['city']}")
                    st.markdown(f"**Urgency:** {_urgency_badge(req['urgency'])}")
                    if req.get("additional_info"):
                        st.markdown(f"**Notes:** {req['additional_info']}")
                    st.caption(f"Posted: {req['posted_at']}")

                with action_col:
                    compatible_blood = BLOOD_COMPATIBILITY.get(req['blood_type'], [])
                    st.markdown("**Compatible Blood Types:**")
                    st.markdown("  ·  ".join(compatible_blood))

                st.markdown("---")
                st.markdown("#### 🔍 Compatible Donors")
                matches = find_matches(req)

                if not matches:
                    st.warning(
                        "⚠️ No compatible donors found in the current registry. "
                        "Consider expanding the search or posting on social networks."
                    )
                else:
                    st.success(f"✅ Found **{len(matches)}** compatible donor(s)!")

                    for i, donor in enumerate(matches):
                        same_city = donor["city"] == req["city"]
                        city_badge = "📍 Same city" if same_city else f"🗺️ {donor['city']}"
                        exact_blood = donor["blood_type"] == req["blood_type"]
                        blood_badge = "✅ Exact match" if exact_blood else "🔄 Compatible"

                        d_col1, d_col2, d_col3 = st.columns([3, 2, 2])
                        with d_col1:
                            st.markdown(
                                f"**{i+1}. {donor['name']}**  \n"
                                f"🩸 {donor['blood_type']} {blood_badge} | {city_badge}  \n"
                                f"Donates: {donor['donation_type']}"
                                + (f" | Organs: {', '.join(donor.get('organs',[]))}" if donor.get("organs") else "")
                            )
                        with d_col2:
                            st.markdown(f"📞 `{donor['phone']}`")
                            st.caption(f"Age {donor['age']} | Status: {donor['status']}")
                        with d_col3:
                            if donor["status"] == "Available":
                                if st.button(
                                    "🤝 Confirm Match",
                                    key=f"match_{req['id']}_{donor['id']}",
                                    use_container_width=True,
                                ):
                                    record_match(req["id"], donor["id"])
                                    st.success(
                                        f"✅ Matched **{donor['name']}** with **{req['patient_name']}**! "
                                        "Both parties should be contacted immediately."
                                    )
                                    st.rerun()
                            else:
                                st.caption(f"Status: {donor['status']}")

                # ── AI explanation button ──────────────────────────────────
                st.markdown("---")
                api_key = st.session_state.get("gemini_api_key", "")
                if api_key:
                    if st.button(
                        "🤖 Explain this match with AI",
                        key=f"ai_explain_{req['id']}",
                        use_container_width=True,
                    ):
                        from ai_engine import get_ai_client, build_match_summary_prompt, ask_ai
                        try:
                            with st.spinner("Analysing compatibility with Gemini 2.0 Flash..."):
                                client = get_ai_client(api_key)
                                prompt = build_match_summary_prompt(req, matches)
                                explanation = ask_ai(client, [], prompt)
                            st.info(f"🤖 **AI Analysis:**\n\n{explanation}")
                        except Exception as e:
                            st.error(f"AI error: {e}")
                else:
                    st.caption("💡 Add your Gemini API key in ⚙️ Settings to enable AI match explanations.")

with tab2:
    if all_requests:
        import pandas as pd
        df = pd.DataFrame(all_requests)
        cols = ["id", "patient_name", "blood_type", "city", "donation_type",
                "urgency", "hospital", "status", "posted_at"]
        df = df[cols]
        df.columns = ["ID", "Patient", "Blood Type", "City", "Type", "Urgency", "Hospital", "Status", "Posted At"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No requests in the system yet.")

# ── Confirmed Matches log ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("🤝 Confirmed Matches")

if st.session_state.matches:
    import pandas as pd
    matches_log = []
    donor_map  = {d["id"]: d for d in st.session_state.donors}
    req_map    = {r["id"]: r for r in st.session_state.requests}

    for m in st.session_state.matches:
        d = donor_map.get(m["donor_id"], {})
        r = req_map.get(m["req_id"],   {})
        matches_log.append({
            "Match Time":    m["matched_at"],
            "Patient":       r.get("patient_name", m["req_id"]),
            "Donor":         d.get("name",  m["donor_id"]),
            "Blood Type":    d.get("blood_type", "—"),
            "City":          r.get("city", "—"),
            "Hospital":      r.get("hospital", "—"),
        })

    st.dataframe(pd.DataFrame(matches_log), use_container_width=True, hide_index=True)
else:
    st.info("No matches confirmed yet. Find an open request above to start matching.")
