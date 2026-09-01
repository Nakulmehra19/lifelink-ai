"""Post urgent donation request page."""
import streamlit as st
import pandas as pd
from data_store import (
    add_request, ALL_BLOOD_TYPES, ORGAN_TYPES, DONATION_TYPES, INDIAN_CITIES
)

URGENCY_LEVELS = ["Critical", "High", "Moderate"]

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🚨 Post an Urgent Request")
st.caption(
    "If a patient urgently needs blood or an organ transplant, post a request here. "
    "Our AI matching engine will instantly scan for compatible donors."
)
st.divider()

# ── Layout ────────────────────────────────────────────────────────────────────
form_col, info_col = st.columns([3, 2], gap="large")

with form_col:
    # ── Section 1: Patient Information ───────────────────────────────────────
    with st.container(border=True):
        st.subheader("🧑‍⚕️ Patient Information")
        patient_name = st.text_input("Patient Full Name *", placeholder="e.g. Ravi Kumar")
        hosp_col, city_col = st.columns(2)
        with hosp_col:
            hospital = st.text_input("Hospital Name *", placeholder="e.g. AIIMS Delhi")
        with city_col:
            city = st.selectbox("Patient City *", INDIAN_CITIES)
        contact = st.text_input(
            "Contact Person / Phone *",
            placeholder="Doctor or family contact number"
        )

    # ── Section 2: Medical Requirement ───────────────────────────────────────
    with st.container(border=True):
        st.subheader("🩺 Medical Requirement")
        bt_col, dtype_col, urg_col = st.columns(3)
        with bt_col:
            blood_type = st.selectbox("Required Blood Type *", ALL_BLOOD_TYPES)
        with dtype_col:
            donation_type = st.selectbox(
                "Requirement Type *", DONATION_TYPES,
                help="Select Blood, Organ, or Both."
            )
        with urg_col:
            urgency = st.selectbox(
                "Urgency Level *", URGENCY_LEVELS,
                help="Critical = life-threatening within hours | High = within days | Moderate = scheduled."
            )

        organs = []
        if donation_type in ("Organ", "Both"):
            organs = st.multiselect(
                "Required Organ(s) *",
                ORGAN_TYPES,
                help="Select all organs needed by the patient."
            )
            if not organs:
                st.warning("Please select at least one required organ.")

        additional_info = st.text_area(
            "Additional Medical Notes (optional)",
            placeholder="e.g. patient is on dialysis, specific HLA typing required, surgery scheduled for...",
            height=80,
        )

    # ── Urgency alert preview ─────────────────────────────────────────────────
    if urgency == "Critical":
        st.error("🔴 **Critical** — this request will be flagged at the top of the matching queue.")
    elif urgency == "High":
        st.warning("🟠 **High Urgency** — matching will prioritise nearby donors immediately.")
    else:
        st.info("🟡 **Moderate** — request will be queued and matched as donors become available.")

    submitted = st.button("🚨 Post Request", type="primary", use_container_width=True)

    if submitted:
        errors = []
        if not patient_name.strip():
            errors.append("Patient name is required.")
        if not hospital.strip():
            errors.append("Hospital name is required.")
        if not contact.strip():
            errors.append("Contact person/phone is required.")
        if donation_type in ("Organ", "Both") and not organs:
            errors.append("Please select at least one required organ.")

        if errors:
            for e in errors:
                st.error(f"⚠️ {e}")
        else:
            req = {
                "patient_name":    patient_name.strip(),
                "hospital":        hospital.strip(),
                "contact":         contact.strip(),
                "blood_type":      blood_type,
                "donation_type":   donation_type,
                "organs":          organs,
                "urgency":         urgency,
                "additional_info": additional_info.strip(),
                "city":            city,
            }
            req_id = add_request(req)
            st.success(
                f"✅ **Request posted successfully!** Request ID: `{req_id}`  \n"
                "Go to **🔗 Find Matches** to see compatible donors instantly."
            )
            if urgency == "Critical":
                st.balloons()

with info_col:
    # ── Guidelines ────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("📌 Request Guidelines")
        with st.expander("Before Posting", expanded=True):
            st.info(
                "- Confirm the patient's blood type with a doctor\n"
                "- Have the hospital name and ward number ready\n"
                "- For organ requests, note if HLA typing has been done"
            )
        with st.expander("After Posting"):
            st.success(
                "1. Go to **Find Matches** to see compatible donors\n"
                "2. Use **AI Assistant** for guidance on next steps\n"
                "3. Contact matched donors through the platform"
            )
        with st.expander("🆘 Emergency Contacts"):
            st.error(
                "**National Blood Transfusion Council**  \n"
                "📞 1800-11-2202 (Toll-free)  \n\n"
                "Or contact your nearest blood bank directly."
            )

    # ── Live stats ────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("📊 Current Status")
        critical_open = [
            r for r in st.session_state.requests
            if r["urgency"] == "Critical" and r["status"] == "Open"
        ]
        if critical_open:
            st.error(
                f"🔴 **{len(critical_open)} critical request(s) currently open** "
                "— please help if you can!"
            )

        total_open = sum(1 for r in st.session_state.requests if r["status"] == "Open")
        total_matched = sum(1 for r in st.session_state.requests if r["status"] == "Matched")
        m1, m2 = st.columns(2)
        m1.metric("Open Requests", total_open)
        m2.metric("Matched", total_matched)

st.divider()

# ── All requests table ────────────────────────────────────────────────────────
st.subheader("📋 All Requests")

if st.session_state.requests:
    df = pd.DataFrame(st.session_state.requests)
    show_cols = ["id", "patient_name", "blood_type", "city", "donation_type",
                 "urgency", "hospital", "status", "posted_at"]
    df = df[show_cols]
    df.columns = ["ID", "Patient", "Blood Type", "City", "Type", "Urgency", "Hospital", "Status", "Posted At"]

    def highlight_urgency(val):
        color_map = {"Critical": "#ffcccc", "High": "#ffe5cc", "Moderate": "#fffacc"}
        return f"background-color: {color_map.get(val, 'white')}"

    st.dataframe(
        df.style.map(highlight_urgency, subset=["Urgency"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No requests posted yet.")
