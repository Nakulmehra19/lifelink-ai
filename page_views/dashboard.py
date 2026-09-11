"""
LifeLink — Analytics Dashboard
Modern redesign: mixed chart types (pie, donut, horizontal bar, bar),
color-coded sections, compact layout, zero hardcoded data.

Rules:
  - Native Streamlit + Plotly only (no HTML/CSS/JS injection).
  - No unsafe_allow_html.
  - All values from session-state; no new Supabase calls.
  - Division-by-zero guarded throughout.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_store import ALL_BLOOD_TYPES, ORGAN_TYPES, MATCH_STATUSES

# ── Plotly shared config ──────────────────────────────────────────────────────
_PLOT_CONFIG  = {"displayModeBar": False}
_PLOT_MARGIN  = dict(t=10, b=10, l=10, r=10)
_PIE_LAYOUT   = dict(
    margin=_PLOT_MARGIN,
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
    height=260,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

# ── Data ──────────────────────────────────────────────────────────────────────
donors   = st.session_state.get("donors",   [])
requests = st.session_state.get("requests", [])
matches  = st.session_state.get("matches",  [])

# ── Pre-compute every metric once ────────────────────────────────────────────
total_donors      = len(donors)
verified_donors   = sum(1 for d in donors   if d.get("verification_status") == "Verified")
available_donors  = sum(1 for d in donors   if d.get("status")              == "Available"
                                             and d.get("verification_status") == "Verified")
total_requests    = len(requests)
open_requests     = sum(1 for r in requests if r.get("status")  == "Open")
critical_open     = sum(1 for r in requests if r.get("urgency") == "Critical" and r.get("status") == "Open")
high_open         = sum(1 for r in requests if r.get("urgency") == "High"     and r.get("status") == "Open")
moderate_open     = sum(1 for r in requests if r.get("urgency") == "Moderate" and r.get("status") == "Open")
total_matches     = len(matches)
pending_m         = sum(1 for m in matches if m.get("match_status") == "Pending")
contacted_m       = sum(1 for m in matches if m.get("match_status") == "Contacted")
accepted_m        = sum(1 for m in matches if m.get("match_status") == "Accepted")
completed_m       = sum(1 for m in matches if m.get("match_status") == "Completed")
cancelled_m       = sum(1 for m in matches if m.get("match_status") == "Cancelled")
confirmed_matches = accepted_m + completed_m
non_cancelled     = total_matches - cancelled_m
success_rate      = round(confirmed_matches / non_cancelled * 100, 1) if non_cancelled > 0 else 0.0
fulfilled_reqs    = sum(1 for r in requests if r.get("status")   == "Matched")
matched_req_count = fulfilled_reqs
match_progress    = round(matched_req_count / total_requests * 100, 1) if total_requests > 0 else 0.0
lives_saved       = confirmed_matches if confirmed_matches > 0 else total_matches
donor_ids_in_matches = {m.get("donor_id") for m in matches if m.get("donor_id")}

# Donation type frequencies (full data, no filter)
_dtc: dict = {}
for _d in donors:
    _k = _d.get("donation_type", "Unknown")
    _dtc[_k] = _dtc.get(_k, 0) + 1
most_common_dtype = max(_dtc, key=_dtc.get) if _dtc else "—"

# ─────────────────────────────────────────────────────────────────────────────
# FILTERS  (collapsed)
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("🔎 Dashboard Filters", expanded=False):
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    all_cities    = sorted(({d.get("city","") for d in donors} | {r.get("city","") for r in requests}) - {""})
    all_don_types = ["All", "Blood", "Organ", "Both"]
    all_blood     = ["All"] + ALL_BLOOD_TYPES
    all_req_stat  = ["All", "Open", "Matched", "Closed"]
    all_urgency   = ["All", "Critical", "High", "Moderate"]

    f_city   = fc1.selectbox("City",           ["All"] + all_cities, key="dash_f_city")
    f_blood  = fc2.selectbox("Blood Type",     all_blood,            key="dash_f_blood")
    f_dtype  = fc3.selectbox("Donation Type",  all_don_types,        key="dash_f_dtype")
    f_status = fc4.selectbox("Request Status", all_req_stat,         key="dash_f_status")
    f_urg    = fc5.selectbox("Urgency",         all_urgency,          key="dash_f_urg")

def _filter(donor_list, request_list):
    d = donor_list[:]
    r = request_list[:]
    if f_city   != "All":
        d = [x for x in d if x.get("city")          == f_city]
        r = [x for x in r if x.get("city")          == f_city]
    if f_blood  != "All":
        d = [x for x in d if x.get("blood_type")    == f_blood]
        r = [x for x in r if x.get("blood_type")    == f_blood]
    if f_dtype  != "All":
        d = [x for x in d if x.get("donation_type") == f_dtype]
        r = [x for x in r if x.get("donation_type") == f_dtype]
    if f_status != "All":
        r = [x for x in r if x.get("status")        == f_status]
    if f_urg    != "All":
        r = [x for x in r if x.get("urgency")       == f_urg]
    return d, r

f_donors, f_requests = _filter(donors, requests)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.title("🩸 LifeLink Dashboard")
st.caption(
    "Real-time insights into donor-recipient connections and life-saving impact."
)
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS  (2 rows × 3 columns = 6 metrics)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📊 Key Metrics")

k1, k2, k3 = st.columns(3)
k1.metric("🩸 Total Donors",    total_donors,
          delta=f"{verified_donors} verified", delta_color="normal")
k2.metric("📋 Total Requests",  total_requests,
          delta=f"{open_requests} open", delta_color="off")
k3.metric("✅ Verified Donors", verified_donors,
          delta=f"{available_donors} available now", delta_color="normal")

k4, k5, k6 = st.columns(3)
k4.metric("🤝 Confirmed Matches",     confirmed_matches,
          delta=f"{success_rate}% success", delta_color="normal")
k5.metric("⏳ Pending Requests",      open_requests,
          delta="Urgent!" if critical_open else "Stable",
          delta_color="inverse" if critical_open else "off")
k6.metric("❤️ Lives Potentially Saved", lives_saved)

if total_requests > 0:
    st.progress(
        min(matched_req_count / total_requests, 1.0),
        text=f"Matching Progress — {matched_req_count} of {total_requests} requests matched ({match_progress}%)",
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD SUMMARY  (data-driven, 2 columns)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("💡 Dashboard Summary")

_insights = []
if available_donors > 0:
    _insights.append(("success", f"✅ **{available_donors}** verified donor(s) are available and ready."))
if critical_open > 0:
    _insights.append(("error",   f"🚨 **{critical_open}** critical request(s) are open — immediate action needed."))
if high_open > 0:
    _insights.append(("warning", f"⚠️ **{high_open}** high-priority request(s) are awaiting a match."))
if success_rate > 0:
    _insights.append(("info",    f"📈 AI match success rate is **{success_rate}%** ({confirmed_matches}/{non_cancelled} active matches confirmed)."))
if most_common_dtype != "—":
    _insights.append(("info",    f"🏥 Most common donation type among donors: **{most_common_dtype}**."))
if len(donor_ids_in_matches) > 0:
    _insights.append(("success", f"🤝 **{len(donor_ids_in_matches)}** donor(s) are currently in active matches."))
if not _insights:
    _insights.append(("info", "ℹ️ No data available yet. Register donors and requests to see insights."))

_c1, _c2 = st.columns(2)
_mid = (len(_insights) + 1) // 2
for _typ, _msg in _insights[:_mid]:
    getattr(_c1, f"st_{_typ}" if False else _typ)(_msg)   # resolved below
for _typ, _msg in _insights[_mid:]:
    getattr(_c2, f"st_{_typ}" if False else _typ)(_msg)

# Note: st.columns return objects with .success/.warning/.error/.info methods
# The loop above works because Streamlit column objects expose those methods.
del _c1, _c2, _insights, _mid

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# AI MATCHING  |  REQUEST URGENCY  (side-by-side donuts)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🤖 AI Matching Performance  &  🚨 Request Urgency")

match_col, urg_col = st.columns(2, gap="large")

# ── AI Matching donut ────────────────────────────────────────────────────────
with match_col:
    with st.container(border=True):
        # headline metric
        sr_col, _ = st.columns([2, 1])
        sr_col.metric("🎯 Match Success Rate", f"{success_rate}%",
                      delta=f"{confirmed_matches} confirmed", delta_color="normal")

        if total_matches > 0:
            ms_labels = ["Pending", "Contacted", "Accepted", "Completed", "Cancelled"]
            ms_values = [pending_m, contacted_m, accepted_m, completed_m, cancelled_m]
            ms_colors = ["#F59E0B", "#3B82F6", "#10B981", "#059669", "#EF4444"]

            fig_match = go.Figure(go.Pie(
                labels=ms_labels,
                values=ms_values,
                hole=0.55,
                marker_colors=ms_colors,
                textinfo="percent+label",
                hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            ))
            fig_match.add_annotation(
                text=f"<b>{total_matches}</b><br>matches",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14),
            )
            fig_match.update_layout(**_PIE_LAYOUT)
            st.plotly_chart(fig_match, use_container_width=True, config=_PLOT_CONFIG)

            am1, am2, am3 = st.columns(3)
            am1.metric("⏳ Pending",   pending_m)
            am2.metric("📞 Contacted", contacted_m)
            am3.metric("🏁 Completed", completed_m)
        else:
            st.info("No match data yet.")

        if len(donor_ids_in_matches):
            st.success(f"👤 {len(donor_ids_in_matches)} donor(s) active in matches.")
        req_awaiting = sum(
            1 for r in requests
            if r.get("status") == "Open" and r.get("verification_status") == "Approved"
        )
        if req_awaiting:
            st.warning(f"📭 {req_awaiting} approved request(s) still awaiting a match.")

# ── Request Urgency donut ────────────────────────────────────────────────────
with urg_col:
    with st.container(border=True):
        urg_labels  = ["Critical", "High", "Moderate"]
        urg_values  = [critical_open, high_open, moderate_open]
        urg_colors  = ["#EF4444", "#F97316", "#3B82F6"]

        if any(v > 0 for v in urg_values):
            fig_urg = go.Figure(go.Pie(
                labels=urg_labels,
                values=urg_values,
                hole=0.55,
                marker_colors=urg_colors,
                textinfo="percent+label",
                hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            ))
            fig_urg.add_annotation(
                text=f"<b>{sum(urg_values)}</b><br>open",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14),
            )
            fig_urg.update_layout(**_PIE_LAYOUT)
            st.plotly_chart(fig_urg, use_container_width=True, config=_PLOT_CONFIG)
        else:
            st.info("No open requests matching current filters.")

        u1, u2, u3 = st.columns(3)
        u1.metric("🔴 Critical", critical_open)
        u2.metric("🟠 High",     high_open)
        u3.metric("🔵 Moderate", moderate_open)

        if critical_open:
            st.error(f"🚨 {critical_open} critical request(s) — immediate action needed.")
        if high_open:
            st.warning(f"⚠️ {high_open} high-priority request(s) need attention.")
        if moderate_open:
            st.info(f"ℹ️ {moderate_open} moderate request(s) in queue.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# LIFE-SAVING IMPACT  (metric cards, no chart overload)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("❤️ Life-Saving Impact")

with st.container(border=True):
    imp1, imp2, imp3, imp4 = st.columns(4)
    imp1.metric("❤️ Lives Potentially Saved", lives_saved)
    imp2.metric("✅ Confirmed Matches",        confirmed_matches)
    imp3.metric("🏥 Fulfilled Requests",       fulfilled_reqs)
    imp4.metric("🔬 Verified Donors",          verified_donors)

    if lives_saved > 0:
        st.success(
            f"🎉 LifeLink has facilitated up to **{lives_saved}** life-saving connection(s) "
            f"through **{confirmed_matches}** confirmed match(es) and **{fulfilled_reqs}** fulfilled request(s)."
        )
    elif total_matches > 0:
        st.info(
            f"🤝 {total_matches} match(es) in progress — confirmations pending."
        )
    else:
        st.info("Waiting for the first donor-recipient match.")

    # Organ pool summary (only if organ donors exist)
    organ_donors = [d for d in donors if d.get("donation_type") in ("Organ", "Both")]
    if organ_donors:
        oc: dict = {o: 0 for o in ORGAN_TYPES}
        for _d in organ_donors:
            for _organ in (_d.get("organs") or []):
                if _organ in oc:
                    oc[_organ] += 1
        active_oc = {k: v for k, v in oc.items() if v > 0}
        if active_oc:
            st.caption(f"🫀 Organ pool: {len(organ_donors)} organ donor(s) — "
                       + ", ".join(f"{k}: {v}" for k, v in sorted(active_oc.items(), key=lambda x: -x[1])))

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# DONOR ANALYTICS  (PIE for blood group + verification; BAR for donation type)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("👥 Donor Insights")

da_col1, da_col2, da_col3 = st.columns(3, gap="medium")

# A) Blood Group Distribution — PIE chart
with da_col1:
    with st.container(border=True):
        st.caption("🩸 Blood Group Distribution")
        if f_donors:
            bt_counts = {bt: 0 for bt in ALL_BLOOD_TYPES}
            for _d in f_donors:
                _bt = _d.get("blood_type", "")
                if _bt in bt_counts:
                    bt_counts[_bt] += 1
            _bt_labels = [k for k, v in bt_counts.items() if v > 0]
            _bt_values = [v for v in bt_counts.values() if v > 0]
            if _bt_labels:
                _bg_colors = [
                    "#EF4444","#F97316","#F59E0B","#10B981",
                    "#3B82F6","#8B5CF6","#EC4899","#14B8A6",
                ]
                fig_bt = go.Figure(go.Pie(
                    labels=_bt_labels,
                    values=_bt_values,
                    hole=0.45,
                    marker_colors=_bg_colors[:len(_bt_labels)],
                    textinfo="percent+label",
                    hovertemplate="%{label}: %{value}<extra></extra>",
                ))
                fig_bt.update_layout(**_PIE_LAYOUT)
                st.plotly_chart(fig_bt, use_container_width=True, config=_PLOT_CONFIG)
            else:
                st.info("No blood type data.")
        else:
            st.info("No donor data for selected filters.")

# B) Donation Type — BAR chart
with da_col2:
    with st.container(border=True):
        st.caption("🏥 Donation Type")
        if f_donors:
            _dtc2: dict = {}
            for _d in f_donors:
                _k2 = _d.get("donation_type", "Unknown")
                _dtc2[_k2] = _dtc2.get(_k2, 0) + 1
            if _dtc2:
                fig_dt = px.bar(
                    x=list(_dtc2.keys()),
                    y=list(_dtc2.values()),
                    labels={"x": "Type", "y": "Donors"},
                    color=list(_dtc2.keys()),
                    color_discrete_map={"Blood": "#EF4444", "Organ": "#8B5CF6", "Both": "#10B981"},
                )
                fig_dt.update_layout(
                    margin=_PLOT_MARGIN, height=260, showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
                )
                st.plotly_chart(fig_dt, use_container_width=True, config=_PLOT_CONFIG)
        else:
            st.info("No donor data for selected filters.")

# C) Donor Verification Status — DONUT chart
with da_col3:
    with st.container(border=True):
        st.caption("✅ Verification Status")
        if f_donors:
            _vc: dict = {}
            for _d in f_donors:
                _v = _d.get("verification_status", "Unknown")
                _vc[_v] = _vc.get(_v, 0) + 1
            _v_colors = {"Verified": "#10B981", "Pending": "#F59E0B",
                         "Rejected": "#EF4444", "Suspended": "#6B7280"}
            if _vc:
                fig_vc = go.Figure(go.Pie(
                    labels=list(_vc.keys()),
                    values=list(_vc.values()),
                    hole=0.5,
                    marker_colors=[_v_colors.get(k, "#94A3B8") for k in _vc],
                    textinfo="percent+label",
                    hovertemplate="%{label}: %{value}<extra></extra>",
                ))
                fig_vc.update_layout(**_PIE_LAYOUT)
                st.plotly_chart(fig_vc, use_container_width=True, config=_PLOT_CONFIG)
                _pv = _vc.get("Pending", 0)
                if _pv:
                    st.warning(f"⚠️ {_pv} donor(s) pending verification.")
        else:
            st.info("No donor data for selected filters.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# REQUEST ANALYTICS  (BAR for status; PIE for donation type; horizontal bar for blood type)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📋 Request Insights")

ra_col1, ra_col2, ra_col3 = st.columns(3, gap="medium")

# A) Request Status — BAR chart
with ra_col1:
    with st.container(border=True):
        st.caption("📊 Request Status")
        if f_requests:
            _rsc: dict = {}
            for _r in f_requests:
                _s = _r.get("status", "Unknown")
                _rsc[_s] = _rsc.get(_s, 0) + 1
            if _rsc:
                _rs_colors = {"Open": "#F59E0B", "Matched": "#10B981",
                              "Closed": "#6B7280", "Fulfilled": "#3B82F6"}
                fig_rs = px.bar(
                    x=list(_rsc.keys()),
                    y=list(_rsc.values()),
                    labels={"x": "Status", "y": "Requests"},
                    color=list(_rsc.keys()),
                    color_discrete_map=_rs_colors,
                )
                fig_rs.update_layout(
                    margin=_PLOT_MARGIN, height=260, showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
                )
                st.plotly_chart(fig_rs, use_container_width=True, config=_PLOT_CONFIG)
        else:
            st.info("No request data for selected filters.")

# B) Requested Donation Type — PIE chart
with ra_col2:
    with st.container(border=True):
        st.caption("🏥 Requested Donation Type")
        if f_requests:
            _rdtc: dict = {}
            for _r in f_requests:
                _dt = _r.get("donation_type", "Unknown")
                _rdtc[_dt] = _rdtc.get(_dt, 0) + 1
            if _rdtc:
                _rdt_colors = {"Blood": "#EF4444", "Organ": "#8B5CF6", "Both": "#10B981"}
                fig_rdt = go.Figure(go.Pie(
                    labels=list(_rdtc.keys()),
                    values=list(_rdtc.values()),
                    hole=0.45,
                    marker_colors=[_rdt_colors.get(k, "#94A3B8") for k in _rdtc],
                    textinfo="percent+label",
                    hovertemplate="%{label}: %{value}<extra></extra>",
                ))
                fig_rdt.update_layout(**_PIE_LAYOUT)
                st.plotly_chart(fig_rdt, use_container_width=True, config=_PLOT_CONFIG)
        else:
            st.info("No request data for selected filters.")

# C) Requested Blood Types — horizontal bar
with ra_col3:
    with st.container(border=True):
        st.caption("🩸 Requested Blood Types")
        if f_requests:
            _rbtc: dict = {bt: 0 for bt in ALL_BLOOD_TYPES}
            for _r in f_requests:
                _bt2 = _r.get("blood_type", "")
                if _bt2 in _rbtc:
                    _rbtc[_bt2] += 1
            _rbtc_filt = {k: v for k, v in _rbtc.items() if v > 0}
            if _rbtc_filt:
                _rbt_df = (
                    pd.DataFrame({"Blood Type": list(_rbtc_filt.keys()),
                                  "Requests":   list(_rbtc_filt.values())})
                    .sort_values("Requests", ascending=True)
                )
                fig_rbt = px.bar(
                    _rbt_df, x="Requests", y="Blood Type",
                    orientation="h",
                    color="Requests",
                    color_continuous_scale=["#FECACA", "#EF4444", "#991B1B"],
                )
                fig_rbt.update_layout(
                    margin=_PLOT_MARGIN, height=260, showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                    xaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
                    yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_rbt, use_container_width=True, config=_PLOT_CONFIG)
            else:
                st.info("No blood type data for selected filters.")
        else:
            st.info("No request data for selected filters.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# LOCATION OVERVIEW  (horizontal bar charts)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📍 Location Overview")

loc_d_col, loc_r_col = st.columns(2, gap="large")

with loc_d_col:
    with st.container(border=True):
        st.caption("👥 Donors by City (Top 10)")
        if f_donors:
            _cd: dict = {}
            for _d in f_donors:
                _c = _d.get("city", "Unknown")
                _cd[_c] = _cd.get(_c, 0) + 1
            if _cd:
                _cd_df = (
                    pd.DataFrame({"City": list(_cd.keys()), "Donors": list(_cd.values())})
                    .sort_values("Donors", ascending=True)
                    .tail(10)
                )
                fig_cd = px.bar(
                    _cd_df, x="Donors", y="City", orientation="h",
                    color="Donors",
                    color_continuous_scale=["#BFDBFE", "#3B82F6", "#1E3A8A"],
                )
                fig_cd.update_layout(
                    margin=_PLOT_MARGIN,
                    height=max(200, min(len(_cd), 10) * 30 + 40),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                    xaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
                    yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_cd, use_container_width=True, config=_PLOT_CONFIG)
        else:
            st.info("No donor location data for selected filters.")

with loc_r_col:
    with st.container(border=True):
        st.caption("📋 Requests by City (Top 10)")
        if f_requests:
            _cr: dict = {}
            for _r in f_requests:
                _c = _r.get("city", "Unknown")
                _cr[_c] = _cr.get(_c, 0) + 1
            if _cr:
                _cr_df = (
                    pd.DataFrame({"City": list(_cr.keys()), "Requests": list(_cr.values())})
                    .sort_values("Requests", ascending=True)
                    .tail(10)
                )
                fig_cr = px.bar(
                    _cr_df, x="Requests", y="City", orientation="h",
                    color="Requests",
                    color_continuous_scale=["#FED7AA", "#F97316", "#7C2D12"],
                )
                fig_cr.update_layout(
                    margin=_PLOT_MARGIN,
                    height=max(200, min(len(_cr), 10) * 30 + 40),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                    xaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
                    yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_cr, use_container_width=True, config=_PLOT_CONFIG)
        else:
            st.info("No request location data for selected filters.")

# City-wise comparison (grouped bar)
if f_donors and f_requests:
    with st.container(border=True):
        st.caption("🗺️ City-wise Donor vs Request Comparison")
        _cmp_cities = sorted(
            {_d.get("city", "") for _d in f_donors} |
            {_r.get("city", "") for _r in f_requests}
        )
        _cmp_rows = []
        for _city in _cmp_cities:
            if not _city:
                continue
            _cmp_rows.append({
                "City":     _city,
                "Donors":   sum(1 for _d in f_donors   if _d.get("city") == _city),
                "Requests": sum(1 for _r in f_requests if _r.get("city") == _city),
            })
        if _cmp_rows:
            _cmp_df = pd.DataFrame(_cmp_rows).sort_values("Donors", ascending=False)
            fig_cmp = px.bar(
                _cmp_df.melt(id_vars="City", var_name="Type", value_name="Count"),
                x="City", y="Count", color="Type", barmode="group",
                color_discrete_map={"Donors": "#3B82F6", "Requests": "#F97316"},
            )
            fig_cmp.update_layout(
                margin=_PLOT_MARGIN, height=280,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_cmp, use_container_width=True, config=_PLOT_CONFIG)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL REQUESTS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🚨 Critical Requests")

_crit = [r for r in requests if r.get("urgency") == "Critical" and r.get("status") == "Open"]

if _crit:
    st.error(f"🚨 {len(_crit)} critical open request(s) require immediate attention.")
    _want = ["patient_name", "blood_type", "donation_type", "urgency", "city",
             "hospital", "verification_status", "posted_at"]
    _have = [c for c in _want if any(c in r for r in _crit)]
    _crit_rows = [{col: r.get(col, "") for col in _have} for r in _crit]
    _crit_df   = pd.DataFrame(_crit_rows)
    _crit_df.columns = [c.replace("_", " ").title() for c in _crit_df.columns]
    st.dataframe(_crit_df, use_container_width=True, hide_index=True)
else:
    st.success("✅ No critical open requests at this time.")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# RECENT ACTIVITY  (expandable detailed records — no extra DB calls)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🗂️ Recent Activity")

with st.expander("👥 Full Donor Registry"):
    if donors:
        _d_want = ["id", "name", "age", "blood_type", "city",
                   "donation_type", "status", "verification_status", "registered_at"]
        _d_have = [c for c in _d_want if c in donors[0]]
        _df_d   = pd.DataFrame(donors)[_d_have]
        _df_d.columns = [c.replace("_", " ").title() for c in _d_have]
        st.dataframe(_df_d, use_container_width=True, hide_index=True)
    else:
        st.info("No donors registered yet.")

with st.expander("📋 Full Request Log"):
    if requests:
        _r_want = ["id", "patient_name", "blood_type", "city", "donation_type",
                   "urgency", "hospital", "status", "verification_status", "posted_at"]
        _r_have = [c for c in _r_want if c in requests[0]]
        _df_r   = pd.DataFrame(requests)[_r_have]
        _df_r.columns = [c.replace("_", " ").title() for c in _r_have]
        st.dataframe(_df_r, use_container_width=True, hide_index=True)
    else:
        st.info("No requests posted yet.")

with st.expander("🤝 Match Log"):
    if matches:
        _donor_map = {d["id"]: d for d in donors}
        _req_map   = {r["id"]: r for r in requests}
        _mrows = []
        for _m in matches:
            _md = _donor_map.get(_m.get("donor_id"), {})
            _mr = _req_map.get(_m.get("req_id"),     {})
            _mrows.append({
                "Matched At":   _m.get("matched_at",   ""),
                "Patient":      _mr.get("patient_name", _m.get("req_id",   "")),
                "Donor":        _md.get("name",         _m.get("donor_id", "")),
                "Blood Type":   _md.get("blood_type",   "—"),
                "City":         _mr.get("city",         "—"),
                "Hospital":     _mr.get("hospital",     "—"),
                "Match Status": _m.get("match_status",  "—"),
            })
        st.dataframe(pd.DataFrame(_mrows), use_container_width=True, hide_index=True)
    else:
        st.info("No confirmed matches yet.")
