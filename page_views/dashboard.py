"""
Dashboard — analytics and visualisation for the donation platform.
Uses only Streamlit native charts (no JS/HTML).
"""
import streamlit as st
import pandas as pd
from data_store import ALL_BLOOD_TYPES, ORGAN_TYPES

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📊 Platform Dashboard")
st.caption("Live statistics and analytics across the LifeLink donation network.")
st.divider()

donors   = st.session_state.donors
requests = st.session_state.requests
matches  = st.session_state.matches

# ── Top KPI row ───────────────────────────────────────────────────────────────
st.subheader("📈 Key Performance Indicators")
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Donors",       len(donors))
k2.metric("Verified Donors",    sum(1 for d in donors   if d.get("verification_status") == "Verified"))
k3.metric("Pledged",            sum(1 for d in donors   if d["status"] == "Pledged"))
k4.metric("Total Requests",     len(requests))
k5.metric("Approved Requests",  sum(1 for r in requests if r.get("verification_status") == "Approved"))
k6.metric("Confirmed Matches",  len(matches))

# ── Match success rate ────────────────────────────────────────────────────────
total_req = len(requests)
matched_r = sum(1 for r in requests if r["status"] == "Matched")
open_r    = sum(1 for r in requests if r["status"] == "Open")
critical  = sum(1 for r in requests if r.get("urgency") == "Critical" and r["status"] == "Open")

if total_req > 0:
    success_rate = round(matched_r / total_req * 100, 1)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Match Success Rate",  f"{success_rate}%",
              delta=f"{matched_r} fulfilled")
    m2.metric("Awaiting Match",      open_r)
    m3.metric("Critical Open",       critical,
              delta="Urgent!" if critical else "Clear",
              delta_color="inverse" if critical else "normal")
    m4.metric("Lives Potentially Saved", len(matches) * 2)
    st.progress(
        min(matched_r / total_req, 1.0),
        text=f"Match Progress: {matched_r} of {total_req} requests fulfilled ({success_rate}%)"
    )
else:
    st.info("No requests posted yet — stats will appear here once activity begins.")

st.divider()

# ── Charts section ────────────────────────────────────────────────────────────
st.subheader("📊 Analytics")
chart_tab1, chart_tab2, chart_tab3 = st.tabs(["🩸 Donor Analytics", "📋 Request Analytics", "🫀 Organ Analytics"])

with chart_tab1:
    col_a, col_b = st.columns(2)

    with col_a:
        with st.container(border=True):
            st.markdown("**Donors by Blood Type**")
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
        with st.container(border=True):
            st.markdown("**Top Cities by Donors**")
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

    col_e, col_f = st.columns(2)
    with col_e:
        with st.container(border=True):
            st.markdown("**Donor Type Breakdown**")
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
        with st.container(border=True):
            st.markdown("**Donor Status Distribution**")
            if donors:
                status_counts = {}
                for d in donors:
                    status_counts[d["status"]] = status_counts.get(d["status"], 0) + 1
                status_df = pd.DataFrame({
                    "Status": list(status_counts.keys()),
                    "Count":  list(status_counts.values()),
                }).set_index("Status")
                st.bar_chart(status_df)
            else:
                st.info("No donor data yet.")

with chart_tab2:
    col_c, col_d = st.columns(2)

    with col_c:
        with st.container(border=True):
            st.markdown("**Requests by Blood Type**")
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
        with st.container(border=True):
            st.markdown("**Requests by Urgency Level**")
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

    with st.container(border=True):
        st.markdown("**Request Status Overview**")
        if requests:
            status_counts = {}
            for r in requests:
                status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
            rs_df = pd.DataFrame({
                "Status": list(status_counts.keys()),
                "Count":  list(status_counts.values()),
            }).set_index("Status")
            st.bar_chart(rs_df)
        else:
            st.info("No request data yet.")

with chart_tab3:
    col_g, col_h = st.columns(2)

    with col_g:
        with st.container(border=True):
            st.markdown("**Organ Availability (Donor Pool)**")
            if donors:
                organ_counts = {o: 0 for o in ORGAN_TYPES}
                for d in donors:
                    for organ in d.get("organs", []):
                        organ_counts[organ] = organ_counts.get(organ, 0) + 1
                organ_df = pd.DataFrame({
                    "Organ":            list(organ_counts.keys()),
                    "Available Donors": list(organ_counts.values()),
                }).sort_values("Available Donors", ascending=False).set_index("Organ")
                st.bar_chart(organ_df)
            else:
                st.info("No organ donor data yet.")

    with col_h:
        with st.container(border=True):
            st.markdown("**Organs Requested**")
            if requests:
                req_organs = {}
                for r in requests:
                    for organ in r.get("organs", []):
                        req_organs[organ] = req_organs.get(organ, 0) + 1
                if req_organs:
                    ro_df = pd.DataFrame({
                        "Organ":    list(req_organs.keys()),
                        "Requests": list(req_organs.values()),
                    }).sort_values("Requests", ascending=False).set_index("Organ")
                    st.bar_chart(ro_df)
                else:
                    st.info("No organ requests yet.")
            else:
                st.info("No request data yet.")

st.divider()

# ── Detailed data tables ──────────────────────────────────────────────────────
st.subheader("🗂️ Detailed Records")

with st.expander("Full Donor Registry"):
    if donors:
        df_d = pd.DataFrame(donors)[["id","name","age","blood_type","city","donation_type","status","registered_at"]]
        df_d.columns = ["ID","Name","Age","Blood Type","City","Donation Type","Status","Registered At"]
        st.dataframe(df_d, use_container_width=True, hide_index=True)
    else:
        st.info("No donors registered yet.")

with st.expander("Full Request Log"):
    if requests:
        df_r = pd.DataFrame(requests)[["id","patient_name","blood_type","city","donation_type","urgency","hospital","status","posted_at"]]
        df_r.columns = ["ID","Patient","Blood Type","City","Type","Urgency","Hospital","Status","Posted At"]
        st.dataframe(df_r, use_container_width=True, hide_index=True)
    else:
        st.info("No requests posted yet.")

with st.expander("Confirmed Matches Log"):
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
        st.info("No confirmed matches yet.")
