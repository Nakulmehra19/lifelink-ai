"""
Dashboard — analytics and visualisation for the donation platform.
Uses only Streamlit native charts (no JS/HTML).
"""
import streamlit as st
import pandas as pd
from data_store import ALL_BLOOD_TYPES, ORGAN_TYPES

st.title("📊 Platform Dashboard")
st.markdown("Live statistics and analytics across the LifeLink donation network.")
st.markdown("---")

donors   = st.session_state.donors
requests = st.session_state.requests
matches  = st.session_state.matches

# ── Top-level KPI row ────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Donors",         len(donors))
k2.metric("Available Donors",     sum(1 for d in donors  if d["status"] == "Available"))
k3.metric("Pledged Donors",       sum(1 for d in donors  if d["status"] == "Pledged"))
k4.metric("Total Requests",       len(requests))
k5.metric("Open Requests",        sum(1 for r in requests if r["status"] == "Open"))
k6.metric("Confirmed Matches",    len(matches))

st.markdown("---")

# ── Charts row 1 ─────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🩸 Donors by Blood Type")
    if donors:
        bt_counts = {bt: 0 for bt in ALL_BLOOD_TYPES}
        for d in donors:
            bt_counts[d["blood_type"]] = bt_counts.get(d["blood_type"], 0) + 1
        bt_df = pd.DataFrame({
            "Blood Type": list(bt_counts.keys()),
            "Donors":     list(bt_counts.values()),
        }).set_index("Blood Type")
        st.bar_chart(bt_df)
    else:
        st.info("No donor data yet.")

with col_b:
    st.subheader("🏙️ Top Cities by Donors")
    if donors:
        city_counts = {}
        for d in donors:
            city_counts[d["city"]] = city_counts.get(d["city"], 0) + 1
        city_df = pd.DataFrame({
            "City":   list(city_counts.keys()),
            "Donors": list(city_counts.values()),
        }).sort_values("Donors", ascending=False).head(10).set_index("City")
        st.bar_chart(city_df)
    else:
        st.info("No donor data yet.")

# ── Charts row 2 ─────────────────────────────────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("📋 Requests by Blood Type")
    if requests:
        rbt = {}
        for r in requests:
            rbt[r["blood_type"]] = rbt.get(r["blood_type"], 0) + 1
        rbt_df = pd.DataFrame({
            "Blood Type": list(rbt.keys()),
            "Requests":   list(rbt.values()),
        }).set_index("Blood Type")
        st.bar_chart(rbt_df)
    else:
        st.info("No request data yet.")

with col_d:
    st.subheader("⚠️ Requests by Urgency Level")
    if requests:
        urgency_counts = {"Critical": 0, "High": 0, "Moderate": 0}
        for r in requests:
            urgency_counts[r["urgency"]] = urgency_counts.get(r["urgency"], 0) + 1
        urg_df = pd.DataFrame({
            "Urgency": list(urgency_counts.keys()),
            "Count":   list(urgency_counts.values()),
        }).set_index("Urgency")
        st.bar_chart(urg_df)
    else:
        st.info("No request data yet.")

st.markdown("---")

# ── Donation type breakdown ───────────────────────────────────────────────────
col_e, col_f = st.columns(2)

with col_e:
    st.subheader("🎁 Donor Donation Type Breakdown")
    if donors:
        dtype_counts = {}
        for d in donors:
            dtype_counts[d["donation_type"]] = dtype_counts.get(d["donation_type"], 0) + 1
        dt_df = pd.DataFrame({
            "Donation Type": list(dtype_counts.keys()),
            "Count":         list(dtype_counts.values()),
        }).set_index("Donation Type")
        st.bar_chart(dt_df)
    else:
        st.info("No donor data yet.")

with col_f:
    st.subheader("🫀 Organ Availability")
    if donors:
        organ_counts = {o: 0 for o in ORGAN_TYPES}
        for d in donors:
            for organ in d.get("organs", []):
                organ_counts[organ] = organ_counts.get(organ, 0) + 1
        organ_df = pd.DataFrame({
            "Organ": list(organ_counts.keys()),
            "Available Donors": list(organ_counts.values()),
        }).sort_values("Available Donors", ascending=False).set_index("Organ")
        st.bar_chart(organ_df)
    else:
        st.info("No organ donor data yet.")

st.markdown("---")

# ── Match success rate ────────────────────────────────────────────────────────
st.subheader("📈 Match Success Overview")
total_req = len(requests)
matched_r = sum(1 for r in requests if r["status"] == "Matched")
open_r    = sum(1 for r in requests if r["status"] == "Open")

if total_req > 0:
    success_rate = round(matched_r / total_req * 100, 1)
    m1, m2, m3 = st.columns(3)
    m1.metric("Match Success Rate",  f"{success_rate}%")
    m2.metric("Requests Fulfilled",  matched_r)
    m3.metric("Still Awaiting",      open_r)

    progress_val = min(matched_r / total_req, 1.0)
    st.progress(progress_val, text=f"{matched_r} of {total_req} requests matched ({success_rate}%)")
else:
    st.info("No requests posted yet — stats will appear here once activity begins.")

st.markdown("---")

# ── Detailed tables ───────────────────────────────────────────────────────────
with st.expander("🗂️ Full Donor Registry"):
    if donors:
        df_d = pd.DataFrame(donors)[["id","name","age","blood_type","city","donation_type","status","registered_at"]]
        df_d.columns = ["ID","Name","Age","Blood Type","City","Donation Type","Status","Registered At"]
        st.dataframe(df_d, use_container_width=True, hide_index=True)
    else:
        st.info("Empty.")

with st.expander("🗂️ Full Request Log"):
    if requests:
        df_r = pd.DataFrame(requests)[["id","patient_name","blood_type","city","donation_type","urgency","hospital","status","posted_at"]]
        df_r.columns = ["ID","Patient","Blood Type","City","Type","Urgency","Hospital","Status","Posted At"]
        st.dataframe(df_r, use_container_width=True, hide_index=True)
    else:
        st.info("Empty.")

with st.expander("🗂️ Confirmed Matches Log"):
    if matches:
        donor_map = {d["id"]: d for d in donors}
        req_map   = {r["id"]: r for r in requests}
        rows = []
        for m in matches:
            d = donor_map.get(m["donor_id"], {})
            r = req_map.get(m["req_id"],   {})
            rows.append({
                "Time":     m["matched_at"],
                "Patient":  r.get("patient_name", m["req_id"]),
                "Donor":    d.get("name",  m["donor_id"]),
                "Blood":    d.get("blood_type","—"),
                "City":     r.get("city","—"),
                "Hospital": r.get("hospital","—"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No matches confirmed yet.")
