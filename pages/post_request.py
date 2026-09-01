"""Post urgent donation request page."""
import streamlit as st
from data_store import (
    add_request, ALL_BLOOD_TYPES, ORGAN_TYPES, DONATION_TYPES, INDIAN_CITIES
)

st.title("🚨 Post an Urgent Request")
st.markdown(
    "If a patient urgently needs blood or an organ transplant, post a request here. "
    "Our AI matching engine will instantly scan for compatible donors."
)
st.markdown("---")

URGENCY_LEVELS = ["Critical", "High", "Moderate"]

left, right = st.columns([3, 2])

with left:
    st.subheader("Patient Information")
    patient_name = st.text_input("Patient Full Name *", placeholder="e.g. Ravi Kumar")
    hospital     = st.text_input("Hospital Name *",     placeholder="e.g. AIIMS Delhi")
    contact      = st.text_input("Contact Person / Phone *", placeholder="Doctor/family contact number")

    st.subheader("Medical Requirement")
    blood_type = st.selectbox("Required Blood Type *", ALL_BLOOD_TYPES)
    donation_type = st.selectbox(
        "Requirement Type *", DONATION_TYPES,
        help="Select Blood, Organ, or Both."
    )

    organs = []
    if donation_type in ("Organ", "Both"):
        organs = st.multiselect(
            "Required Organ(s) *",
            ORGAN_TYPES,
            help="Select all organs needed by the patient."
        )

    urgency = st.selectbox(
        "Urgency Level *", URGENCY_LEVELS,
        help="Critical = life-threatening within hours | High = within days | Moderate = scheduled."
    )

    additional_info = st.text_area(
        "Additional Medical Notes (optional)",
        placeholder="e.g. patient is on dialysis, specific HLA typing required, surgery scheduled for...",
        height=80,
    )

    st.subheader("Location")
    city = st.selectbox("Patient City *", INDIAN_CITIES)

    st.markdown("---")

    if urgency == "Critical":
        st.error("⚠️ **Critical request** — this will be flagged at the top of the matching queue.")
    elif urgency == "High":
        st.warning("🟠 **High urgency** — matching will prioritise nearby donors immediately.")

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
                st.error(e)
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
                f"✅ Request posted successfully! Request ID: **{req_id}**\n\n"
                "Go to **🔗 Find Matches** to see compatible donors instantly."
            )
            if urgency == "Critical":
                st.balloons()

with right:
    st.subheader("📌 Request Guidelines")
    st.info(
        """
        **Before posting:**
        - Confirm the patient's blood type with a doctor
        - Have the hospital name and ward number ready
        - For organ requests, note if HLA typing has been done

        **After posting:**
        - Go to **Find Matches** to see compatible donors
        - Use **AI Assistant** for guidance on next steps
        - Contact matched donors through the platform

        **Emergency?**
        Call **1800-11-2202** (National Blood Transfusion Council)
        or your nearest blood bank directly.
        """
    )

    # Show open critical requests
    critical = [r for r in st.session_state.requests
                if r["urgency"] == "Critical" and r["status"] == "Open"]
    if critical:
        st.error(f"🔴 **{len(critical)} Critical request(s) currently open** — please help if you can!")

    st.metric("📊 Total Open Requests",
              sum(1 for r in st.session_state.requests if r["status"] == "Open"))

st.markdown("---")
st.subheader("📋 All Requests")

if st.session_state.requests:
    import pandas as pd
    df = pd.DataFrame(st.session_state.requests)
    show_cols = ["id", "patient_name", "blood_type", "city", "donation_type",
                 "urgency", "hospital", "status", "posted_at"]
    df = df[show_cols]
    df.columns = ["ID", "Patient", "Blood Type", "City", "Type", "Urgency", "Hospital", "Status", "Posted At"]

    # Color urgency column
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
