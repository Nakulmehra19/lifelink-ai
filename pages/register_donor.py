"""Donor registration page."""
import streamlit as st
from data_store import (
    add_donor, ALL_BLOOD_TYPES, ORGAN_TYPES, DONATION_TYPES, INDIAN_CITIES
)

st.title("📋 Register as a Donor")
st.markdown(
    "Join our network of life-savers. Your registration could save up to **8 lives**. "
    "All information is kept confidential and used only for matching purposes."
)
st.markdown("---")

left, right = st.columns([3, 2])

with left:
    st.subheader("Personal Information")
    name = st.text_input("Full Name *", placeholder="e.g. Arjun Sharma")
    age  = st.number_input("Age *", min_value=18, max_value=65, value=25,
                           help="Donors must be between 18 and 65 years of age.")
    phone = st.text_input("Phone Number *", placeholder="10-digit mobile number")

    st.subheader("Medical Details")
    blood_type = st.selectbox("Blood Type *", ALL_BLOOD_TYPES)
    donation_type = st.selectbox(
        "Donation Type *", DONATION_TYPES,
        help="Select 'Both' if you're willing to donate blood AND organs."
    )

    organs = []
    if donation_type in ("Organ", "Both"):
        organs = st.multiselect(
            "Organ(s) willing to donate *",
            ORGAN_TYPES,
            help="You can select multiple organs. Cornea and bone marrow can be donated by living donors."
        )

    st.subheader("Location")
    city = st.selectbox("City *", INDIAN_CITIES)

    st.markdown("---")
    consent = st.checkbox(
        "I voluntarily consent to register as a donor on the LifeLink platform "
        "and understand that my information will be used solely for matching with recipients. *"
    )

    submitted = st.button("✅ Register as Donor", type="primary", use_container_width=True)

    if submitted:
        # Validation
        errors = []
        if not name.strip():
            errors.append("Full Name is required.")
        if not phone.strip() or not phone.strip().isdigit() or len(phone.strip()) != 10:
            errors.append("A valid 10-digit phone number is required.")
        if donation_type in ("Organ", "Both") and not organs:
            errors.append("Please select at least one organ to donate.")
        if not consent:
            errors.append("You must provide consent to register.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            donor = {
                "name":          name.strip(),
                "age":           int(age),
                "phone":         phone.strip(),
                "blood_type":    blood_type,
                "donation_type": donation_type,
                "organs":        organs,
                "city":          city,
            }
            donor_id = add_donor(donor)
            st.success(f"🎉 Registration successful! Your Donor ID is **{donor_id}**. Thank you for saving lives!")
            st.balloons()

with right:
    st.subheader("ℹ️ Eligibility Guidelines")
    st.info(
        """
        **Blood Donation**
        - Age: 18–65 years
        - Weight: ≥ 45 kg
        - Haemoglobin: ≥ 12.5 g/dL
        - No blood donation in last 3 months
        - No active infection or illness

        **Organ Donation (Living)**
        - Kidneys, partial liver, partial lung
        - Corneas & bone marrow (living donors)

        **Organ Donation (Deceased)**
        - Any adult after brain death
        - Family consent required

        *Always consult a physician before donating.*
        """
    )

    st.subheader("🩸 Blood Type Facts")
    st.warning(
        """
        - **O-** is the universal blood donor
        - **AB+** is the universal plasma donor
        - **AB+** recipients can receive from all types
        - Only **7%** of people are O- worldwide
        """
    )

    # Show current donor count
    avail = sum(1 for d in st.session_state.donors if d["status"] == "Available")
    st.metric("🟢 Registered Donors Available", avail)

st.markdown("---")
st.subheader("📋 All Registered Donors")

if st.session_state.donors:
    import pandas as pd
    df = pd.DataFrame(st.session_state.donors)[
        ["id", "name", "age", "blood_type", "city", "donation_type", "status", "registered_at"]
    ]
    df.columns = ["ID", "Name", "Age", "Blood Type", "City", "Donation Type", "Status", "Registered At"]
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No donors registered yet. Be the first!")
