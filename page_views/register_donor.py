"""Donor registration page."""
import streamlit as st
import pandas as pd
from data_store import (
    add_donor, ALL_BLOOD_TYPES, ORGAN_TYPES, DONATION_TYPES, INDIAN_CITIES
)

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📋 Register as a Donor")
st.caption(
    "Join our network of life-savers. Your registration could save up to **8 lives**. "
    "All information is kept confidential and used only for matching purposes."
)
st.divider()

# ── Layout: form (left) + info panel (right) ──────────────────────────────────
form_col, info_col = st.columns([3, 2], gap="large")

with form_col:
    # ── Section 1: Personal Information ──────────────────────────────────────
    with st.container(border=True):
        st.subheader("👤 Personal Information")
        name_col, age_col = st.columns([2, 1])
        with name_col:
            name = st.text_input("Full Name *", placeholder="e.g. Arjun Sharma")
        with age_col:
            age = st.number_input(
                "Age *", min_value=18, max_value=65, value=25,
                help="Donors must be between 18 and 65 years of age."
            )
        phone_col, city_col = st.columns(2)
        with phone_col:
            phone = st.text_input("Phone Number *", placeholder="10-digit mobile number")
        with city_col:
            city = st.selectbox("City *", INDIAN_CITIES)

    # ── Section 2: Medical Details ────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("🩺 Medical Details")
        bt_col, dtype_col = st.columns(2)
        with bt_col:
            blood_type = st.selectbox("Blood Type *", ALL_BLOOD_TYPES)
        with dtype_col:
            donation_type = st.selectbox(
                "Donation Type *", DONATION_TYPES,
                help="Select 'Both' if you're willing to donate blood AND organs."
            )

        organs = []
        if donation_type in ("Organ", "Both"):
            organs = st.multiselect(
                "Organ(s) Willing to Donate *",
                ORGAN_TYPES,
                help="You can select multiple organs. Cornea and bone marrow can be donated by living donors."
            )
            if not organs:
                st.warning("Please select at least one organ to proceed.")

    # ── Section 3: Consent ────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("✅ Consent")
        consent = st.checkbox(
            "I voluntarily consent to register as a donor on the LifeLink platform "
            "and understand that my information will be used solely for matching with recipients. *"
        )

    submitted = st.button("✅ Register as Donor", type="primary", use_container_width=True)

    if submitted:
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
                st.error(f"⚠️ {e}")
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
            st.success(
                f"🎉 **Registration successful!** Your Donor ID is `{donor_id}`.  \n"
                "Thank you for joining the LifeLink family. You may save up to **8 lives**!"
            )
            st.info(
                "🟡 **Your registration is pending admin verification.** "
                "Once an admin approves your profile, you will become eligible for matching."
            )
            st.balloons()

with info_col:
    # ── Eligibility at a glance ───────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("ℹ️ Eligibility Guidelines")
        with st.expander("🩸 Blood Donation", expanded=True):
            st.info(
                "- Age: **18–65 years**\n"
                "- Weight: ≥ 45 kg\n"
                "- Haemoglobin: ≥ 12.5 g/dL\n"
                "- No donation in the last **3 months**\n"
                "- No active infection or illness"
            )
        with st.expander("🫀 Organ Donation (Living)"):
            st.info(
                "- Kidneys, partial liver, partial lung\n"
                "- Corneas & bone marrow (living donors)\n"
                "- Requires medical evaluation"
            )
        with st.expander("🏥 Organ Donation (Deceased)"):
            st.info(
                "- Any adult after brain death\n"
                "- Family consent required\n"
                "- All major organs can be donated"
            )
        st.caption("*Always consult a physician before donating.*")

    # ── Quick stats ───────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("🩸 Blood Type Facts")
        st.warning(
            "**O−** is the universal blood donor  \n"
            "**AB+** is the universal plasma donor  \n"
            "**AB+** recipients can receive from all types  \n"
            "Only **7%** of people worldwide are O−"
        )
        avail = sum(1 for d in st.session_state.donors if d["status"] == "Available")
        st.metric("🟢 Registered Donors Available", avail)

st.divider()

# ── All registered donors table ───────────────────────────────────────────────
st.subheader("📋 All Registered Donors")

if st.session_state.donors:
    df = pd.DataFrame(st.session_state.donors)[
        ["id", "name", "age", "blood_type", "city", "donation_type", "status", "verification_status", "registered_at"]
    ]
    df.columns = ["ID", "Name", "Age", "Blood Type", "City", "Donation Type", "Status", "Verification", "Registered At"]
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No donors registered yet. Be the first!")
