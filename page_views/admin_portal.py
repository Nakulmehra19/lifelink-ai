"""
Admin Portal — LifeLink
=======================
PROTOTYPE authentication system for academic/demonstration purposes.
In production, replace session-state auth with a proper authentication
solution (OAuth2, hashed-password DB, Streamlit-Authenticator, etc.).

Provides:
  • Admin Login / Logout
  • Admin Dashboard (KPIs)
  • Donor Management (verify / reject / suspend)
  • Request Management (approve / reject / close / fulfill)
  • Match Management (lifecycle progression)
"""
import streamlit as st
import pandas as pd
from data_store import (
    update_donor_verification,
    update_request_verification,
    update_match_status,
    DONOR_VERIFICATION_STATUSES,
    REQUEST_VERIFICATION_STATUSES,
    MATCH_STATUSES,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_admin_creds() -> tuple[str, str]:
    """Read admin credentials from Streamlit secrets (preferred) or fallback."""
    try:
        return (
            st.secrets["admin"]["username"],
            st.secrets["admin"]["password"],
        )
    except Exception:
        # Fallback for local development without secrets.toml
        # IMPORTANT: Replace this with real secrets in production.
        return ("lifelink_admin", "LifeLink@2025")


def _vbadge(status: str) -> str:
    """Return an emoji badge for a verification/match status."""
    return {
        "Pending":   "🟡 Pending",
        "Verified":  "🟢 Verified",
        "Approved":  "🟢 Approved",
        "Rejected":  "🔴 Rejected",
        "Suspended": "⛔ Suspended",
        "Fulfilled": "✅ Fulfilled",
        "Closed":    "⬛ Closed",
        "Contacted": "📞 Contacted",
        "Accepted":  "🤝 Accepted",
        "Completed": "✅ Completed",
        "Cancelled": "❌ Cancelled",
    }.get(status, status)


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN SCREEN
# ─────────────────────────────────────────────────────────────────────────────

def _show_login() -> None:
    st.title("🔐 LifeLink Admin Portal")
    st.caption("Restricted access — authorised personnel only.")
    st.divider()

    with st.container(border=True):
        st.subheader("Admin Login")
        st.info(
            "This portal is for platform administrators only. "
            "If you are a donor or recipient, please use the main navigation."
        )

        username_input = st.text_input("Username", placeholder="Enter admin username")
        password_input = st.text_input("Password", type="password", placeholder="Enter password")

        login_col, _ = st.columns([2, 3])
        with login_col:
            if st.button("🔐 Login", type="primary", use_container_width=True):
                admin_user, admin_pass = _get_admin_creds()
                if username_input.strip() == admin_user and password_input == admin_pass:
                    st.session_state.admin_logged_in = True
                    st.success("✅ Login successful! Welcome, Admin.")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password. Please try again.")

    st.divider()
    st.caption(
        "⚠️ **Security Notice:** This is a prototype authentication system for academic/demo purposes. "
        "Production deployments must use a secure authentication solution."
    )


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DASHBOARD (KPIs)
# ─────────────────────────────────────────────────────────────────────────────

def _show_dashboard() -> None:
    st.subheader("📊 Platform Overview")

    donors   = st.session_state.donors
    requests = st.session_state.requests
    matches  = st.session_state.matches

    # Donor KPIs
    total_d    = len(donors)
    avail_d    = sum(1 for d in donors if d["status"] == "Available")
    pending_d  = sum(1 for d in donors if d.get("verification_status") == "Pending")
    verified_d = sum(1 for d in donors if d.get("verification_status") == "Verified")
    rejected_d = sum(1 for d in donors if d.get("verification_status") == "Rejected")
    suspended_d= sum(1 for d in donors if d.get("verification_status") == "Suspended")
    pledged_d  = sum(1 for d in donors if d["status"] == "Pledged")

    # Request KPIs
    total_r    = len(requests)
    pending_r  = sum(1 for r in requests if r.get("verification_status") == "Pending")
    approved_r = sum(1 for r in requests if r.get("verification_status") == "Approved")
    rejected_r = sum(1 for r in requests if r.get("verification_status") == "Rejected")
    critical_r = sum(1 for r in requests if r.get("urgency") == "Critical" and r["status"] == "Open")
    matched_r  = sum(1 for r in requests if r["status"] == "Matched")

    # Match KPIs
    total_m     = len(matches)
    pending_m   = sum(1 for m in matches if m.get("match_status") == "Pending")
    completed_m = sum(1 for m in matches if m.get("match_status") == "Completed")
    cancelled_m = sum(1 for m in matches if m.get("match_status") == "Cancelled")

    # Alerts
    if pending_d > 0:
        st.warning(f"🟡 **{pending_d} donor(s)** awaiting verification — review in Donor Management.")
    if pending_r > 0:
        st.warning(f"🟡 **{pending_r} request(s)** awaiting approval — review in Request Management.")
    if critical_r > 0:
        st.error(f"🔴 **{critical_r} critical request(s)** currently open and approved.")

    st.divider()

    # ── Donor metrics ─────────────────────────────────────────────────────────
    st.markdown("**🩸 Donor Statistics**")
    dc1, dc2, dc3, dc4, dc5, dc6 = st.columns(6)
    dc1.metric("Total Donors",    total_d)
    dc2.metric("Available",       avail_d)
    dc3.metric("Pledged",         pledged_d)
    dc4.metric("🟡 Pending",      pending_d,   delta="Needs review" if pending_d else None,  delta_color="inverse")
    dc5.metric("🟢 Verified",     verified_d)
    dc6.metric("🔴 Rejected",     rejected_d + suspended_d)

    st.divider()

    # ── Request metrics ───────────────────────────────────────────────────────
    st.markdown("**📋 Request Statistics**")
    rc1, rc2, rc3, rc4, rc5 = st.columns(5)
    rc1.metric("Total Requests",  total_r)
    rc2.metric("🟡 Pending",      pending_r,  delta="Needs review" if pending_r else None, delta_color="inverse")
    rc3.metric("🟢 Approved",     approved_r)
    rc4.metric("🔴 Rejected",     rejected_r)
    rc5.metric("⚠️ Critical Open", critical_r, delta="Urgent!" if critical_r else None,    delta_color="inverse")

    st.divider()

    # ── Match metrics ─────────────────────────────────────────────────────────
    st.markdown("**🤝 Match Statistics**")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Total Matches",   total_m)
    mc2.metric("🟡 Pending",      pending_m)
    mc3.metric("✅ Completed",    completed_m)
    mc4.metric("❌ Cancelled",    cancelled_m)

    # ── Match success rate ────────────────────────────────────────────────────
    if total_r > 0:
        rate = round(matched_r / total_r * 100, 1)
        st.progress(min(matched_r / total_r, 1.0),
                    text=f"Match Success Rate: {matched_r}/{total_r} requests fulfilled ({rate}%)")

    st.divider()

    # ── Recent activity tables ────────────────────────────────────────────────
    t1, t2, t3 = st.tabs(["🟡 Pending Donors", "🟡 Pending Requests", "🤝 Recent Matches"])

    with t1:
        pending_donors = [d for d in donors if d.get("verification_status") == "Pending"]
        if pending_donors:
            df = pd.DataFrame(pending_donors)[["id", "name", "age", "blood_type", "city",
                                                "donation_type", "registered_at"]]
            df.columns = ["ID", "Name", "Age", "Blood Type", "City", "Donation Type", "Registered"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No donors pending verification.")

    with t2:
        pending_reqs = [r for r in requests if r.get("verification_status") == "Pending"]
        if pending_reqs:
            df = pd.DataFrame(pending_reqs)[["id", "patient_name", "blood_type", "city",
                                              "urgency", "hospital", "posted_at"]]
            df.columns = ["ID", "Patient", "Blood Type", "City", "Urgency", "Hospital", "Posted"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No requests pending approval.")

    with t3:
        if matches:
            donor_map = {d["id"]: d for d in donors}
            req_map   = {r["id"]: r for r in requests}
            rows = []
            for m in matches[-10:]:   # last 10
                d = donor_map.get(m["donor_id"], {})
                r = req_map.get(m["req_id"],   {})
                rows.append({
                    "Time":         m["matched_at"],
                    "Patient":      r.get("patient_name", "—"),
                    "Donor":        d.get("name", "—"),
                    "Blood":        d.get("blood_type", "—"),
                    "City":         r.get("city", "—"),
                    "Match Status": _vbadge(m.get("match_status", "Pending")),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No matches recorded yet.")


# ─────────────────────────────────────────────────────────────────────────────
# DONOR MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _show_donor_management() -> None:
    st.subheader("🩸 Donor Management")
    st.caption("Review, verify, and manage all registered donors.")

    donors = st.session_state.donors
    if not donors:
        st.info("No donors registered yet.")
        return

    # ── Filter bar ────────────────────────────────────────────────────────────
    fc1, fc2 = st.columns(2)
    with fc1:
        filter_vs = st.selectbox(
            "Filter by Verification Status",
            ["All"] + DONOR_VERIFICATION_STATUSES,
            key="admin_d_filter_vs",
        )
    with fc2:
        filter_bt = st.selectbox(
            "Filter by Blood Type",
            ["All", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
            key="admin_d_filter_bt",
        )

    filtered = [
        d for d in donors
        if (filter_vs == "All" or d.get("verification_status") == filter_vs)
        and (filter_bt == "All" or d["blood_type"] == filter_bt)
    ]

    st.caption(f"Showing {len(filtered)} of {len(donors)} donors.")
    st.divider()

    if not filtered:
        st.info("No donors match the selected filters.")
        return

    for idx, donor in enumerate(filtered):
        vs     = donor.get("verification_status", "Pending")
        badge  = _vbadge(vs)
        label  = (
            f"{badge}  ·  **{donor['name']}**  ·  "
            f"{donor['blood_type']}  ·  {donor['city']}  ·  {donor['donation_type']}"
        )
        with st.expander(label):
            info_c, action_c = st.columns([3, 2])

            with info_c:
                with st.container(border=True):
                    st.markdown(f"**Donor ID:** `{donor['id']}`")
                    st.markdown(f"**Name:** {donor['name']}")
                    st.markdown(f"**Age:** {donor['age']}  |  **Blood Type:** `{donor['blood_type']}`")
                    st.markdown(f"**Donation Type:** {donor['donation_type']}")
                    if donor.get("organs"):
                        st.markdown(f"**Organs:** {', '.join(donor['organs'])}")
                    st.markdown(f"**City:** {donor['city']}")
                    st.markdown(f"**Phone:** `{donor.get('phone', '—')}`")
                    st.markdown(f"**Operational Status:** {donor['status']}")
                    st.caption(f"Registered: {donor.get('registered_at', '—')}")
                    if donor.get("admin_notes"):
                        st.info(f"📝 Admin notes: {donor['admin_notes']}")

            with action_c:
                with st.container(border=True):
                    st.markdown(f"**Verification:** {badge}")
                    notes_key = f"admin_d_notes_{donor['id']}_{idx}"
                    notes = st.text_input(
                        "Admin Notes (optional)",
                        key=notes_key,
                        placeholder="Reason for action…",
                    )

                    a1, a2 = st.columns(2)
                    with a1:
                        if vs != "Verified":
                            if st.button(
                                "✅ Verify",
                                key=f"d_verify_{donor['id']}_{idx}",
                                use_container_width=True,
                                type="primary",
                            ):
                                update_donor_verification(donor["id"], "Verified", notes)
                                st.success(f"✅ {donor['name']} verified.")
                                st.rerun()
                        else:
                            st.caption("Already verified")

                    with a2:
                        if vs != "Rejected":
                            if st.button(
                                "❌ Reject",
                                key=f"d_reject_{donor['id']}_{idx}",
                                use_container_width=True,
                            ):
                                update_donor_verification(donor["id"], "Rejected", notes)
                                st.warning(f"Donor {donor['name']} rejected.")
                                st.rerun()

                    if vs not in ("Suspended", "Rejected"):
                        if st.button(
                            "⛔ Suspend",
                            key=f"d_suspend_{donor['id']}_{idx}",
                            use_container_width=True,
                        ):
                            update_donor_verification(donor["id"], "Suspended", notes)
                            st.warning(f"Donor {donor['name']} suspended.")
                            st.rerun()

                    if vs == "Suspended":
                        if st.button(
                            "♻️ Reinstate",
                            key=f"d_reinstate_{donor['id']}_{idx}",
                            use_container_width=True,
                        ):
                            update_donor_verification(donor["id"], "Verified", notes)
                            st.success(f"Donor {donor['name']} reinstated.")
                            st.rerun()

    st.divider()
    # ── Full donor table ──────────────────────────────────────────────────────
    with st.expander("📄 Full Donor Registry Table"):
        show_cols = ["id", "name", "age", "blood_type", "city",
                     "donation_type", "status", "verification_status", "registered_at"]
        df = pd.DataFrame(donors)[show_cols]
        df.columns = ["ID", "Name", "Age", "Blood Type", "City",
                      "Donation Type", "Op. Status", "Verification", "Registered"]
        st.dataframe(df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _show_request_management() -> None:
    st.subheader("📋 Request Management")
    st.caption("Review and manage all recipient/urgent donation requests.")

    requests = st.session_state.requests
    if not requests:
        st.info("No requests posted yet.")
        return

    # ── Filter bar ────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        filter_vs = st.selectbox(
            "Filter by Verification Status",
            ["All"] + REQUEST_VERIFICATION_STATUSES,
            key="admin_r_filter_vs",
        )
    with fc2:
        filter_urg = st.selectbox(
            "Filter by Urgency",
            ["All", "Critical", "High", "Moderate"],
            key="admin_r_filter_urg",
        )
    with fc3:
        filter_bt = st.selectbox(
            "Filter by Blood Type",
            ["All", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
            key="admin_r_filter_bt",
        )

    filtered = [
        r for r in requests
        if (filter_vs  == "All" or r.get("verification_status") == filter_vs)
        and (filter_urg == "All" or r.get("urgency") == filter_urg)
        and (filter_bt  == "All" or r["blood_type"] == filter_bt)
    ]

    st.caption(f"Showing {len(filtered)} of {len(requests)} requests.")
    st.divider()

    if not filtered:
        st.info("No requests match the selected filters.")
        return

    urgency_order = {"Critical": 0, "High": 1, "Moderate": 2}
    for idx, req in enumerate(sorted(filtered, key=lambda r: urgency_order.get(r.get("urgency", "Moderate"), 2))):
        vs     = req.get("verification_status", "Pending")
        badge  = _vbadge(vs)
        u_icon = {"Critical": "🔴", "High": "🟠", "Moderate": "🟡"}.get(req.get("urgency", ""), "⚪")
        label  = (
            f"{badge}  ·  {u_icon} {req.get('urgency', '')}  ·  "
            f"**{req['patient_name']}**  ·  {req['blood_type']}  ·  "
            f"{req['hospital']}, {req['city']}"
        )
        with st.expander(label):
            info_c, action_c = st.columns([3, 2])

            with info_c:
                with st.container(border=True):
                    st.markdown(f"**Request ID:** `{req['id']}`")
                    st.markdown(f"**Patient:** {req['patient_name']}")
                    st.markdown(f"**Hospital:** {req['hospital']}, {req['city']}")
                    st.markdown(f"**Blood Type:** `{req['blood_type']}`")
                    st.markdown(f"**Requirement:** {req['donation_type']}")
                    if req.get("organs"):
                        st.markdown(f"**Organs:** {', '.join(req['organs'])}")
                    st.markdown(f"**Urgency:** {u_icon} {req.get('urgency', '—')}")
                    if req.get("additional_info"):
                        st.markdown(f"**Medical Notes:** {req['additional_info']}")
                    st.markdown(f"**Operational Status:** {req['status']}")
                    st.caption(f"Posted: {req.get('posted_at', '—')}")
                    if req.get("admin_notes"):
                        st.info(f"📝 Admin notes: {req['admin_notes']}")

            with action_c:
                with st.container(border=True):
                    st.markdown(f"**Verification:** {badge}")
                    notes_key = f"admin_r_notes_{req['id']}_{idx}"
                    notes = st.text_input(
                        "Admin Notes (optional)",
                        key=notes_key,
                        placeholder="Reason for action…",
                    )

                    b1, b2 = st.columns(2)
                    with b1:
                        if vs != "Approved":
                            if st.button(
                                "✅ Approve",
                                key=f"r_approve_{req['id']}_{idx}",
                                use_container_width=True,
                                type="primary",
                            ):
                                update_request_verification(req["id"], "Approved", notes)
                                st.success(f"✅ Request for {req['patient_name']} approved.")
                                st.rerun()
                        else:
                            st.caption("Already approved")

                    with b2:
                        if vs not in ("Rejected", "Closed"):
                            if st.button(
                                "❌ Reject",
                                key=f"r_reject_{req['id']}_{idx}",
                                use_container_width=True,
                            ):
                                update_request_verification(req["id"], "Rejected", notes)
                                st.warning(f"Request {req['id']} rejected.")
                                st.rerun()

                    b3, b4 = st.columns(2)
                    with b3:
                        if vs not in ("Fulfilled", "Closed", "Rejected"):
                            if st.button(
                                "✅ Mark Fulfilled",
                                key=f"r_fulfill_{req['id']}_{idx}",
                                use_container_width=True,
                            ):
                                update_request_verification(req["id"], "Fulfilled", notes)
                                st.success(f"Request {req['id']} marked as fulfilled.")
                                st.rerun()
                    with b4:
                        if vs not in ("Closed", "Rejected"):
                            if st.button(
                                "⬛ Close",
                                key=f"r_close_{req['id']}_{idx}",
                                use_container_width=True,
                            ):
                                update_request_verification(req["id"], "Closed", notes)
                                st.info(f"Request {req['id']} closed.")
                                st.rerun()

    st.divider()
    with st.expander("📄 Full Requests Table"):
        show_cols = ["id", "patient_name", "blood_type", "city", "donation_type",
                     "urgency", "hospital", "status", "verification_status", "posted_at"]
        df = pd.DataFrame(requests)[show_cols]
        df.columns = ["ID", "Patient", "Blood Type", "City", "Type", "Urgency",
                      "Hospital", "Op. Status", "Verification", "Posted"]
        st.dataframe(df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# MATCH MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _show_match_management() -> None:
    st.subheader("🤝 Match Management")
    st.caption("Review match lifecycles and update their status.")

    matches  = st.session_state.matches
    donors   = st.session_state.donors
    requests = st.session_state.requests

    if not matches:
        st.info("No matches have been confirmed yet. Use Find Matches to create matches.")
        return

    donor_map = {d["id"]: d for d in donors}
    req_map   = {r["id"]: r for r in requests}

    # ── Filter ────────────────────────────────────────────────────────────────
    filter_ms = st.selectbox(
        "Filter by Match Status",
        ["All"] + MATCH_STATUSES,
        key="admin_m_filter",
    )

    for real_idx, m in enumerate(matches):
        ms = m.get("match_status", "Pending")
        if filter_ms != "All" and ms != filter_ms:
            continue

        d = donor_map.get(m["donor_id"], {})
        r = req_map.get(m["req_id"],   {})
        badge = _vbadge(ms)
        label = (
            f"{badge}  ·  "
            f"**{r.get('patient_name', m['req_id'])}**  ←  "
            f"{d.get('name', m['donor_id'])}  ·  "
            f"{d.get('blood_type', '—')}  ·  "
            f"{r.get('city', '—')}"
        )
        with st.expander(label):
            mc1, mc2 = st.columns([3, 2])

            with mc1:
                with st.container(border=True):
                    st.markdown("**Match Details**")
                    st.markdown(f"**Match ID:** `{m['req_id']} → {m['donor_id']}`")
                    st.markdown(f"**Patient:** {r.get('patient_name', '—')}")
                    st.markdown(f"**Hospital:** {r.get('hospital', '—')}, {r.get('city', '—')}")
                    st.markdown(f"**Donor:** {d.get('name', '—')}")
                    st.markdown(f"**Blood Type:** `{d.get('blood_type', '—')}`")
                    st.markdown(f"**Donation Type:** {d.get('donation_type', '—')}")
                    if d.get("organs"):
                        st.markdown(f"**Donor Organs:** {', '.join(d.get('organs', []))}")
                    st.markdown(f"**Donor City:** {d.get('city', '—')}")
                    st.caption(f"Matched at: {m.get('matched_at', '—')}")
                    if m.get("admin_notes"):
                        st.info(f"📝 Admin notes: {m['admin_notes']}")

            with mc2:
                with st.container(border=True):
                    st.markdown(f"**Current Status:** {badge}")
                    notes_key = f"admin_m_notes_{real_idx}"
                    notes = st.text_input(
                        "Admin Notes (optional)",
                        key=notes_key,
                        placeholder="Update notes…",
                    )

                    # Status progression buttons
                    TRANSITIONS = {
                        "Pending":   ["Contacted", "Cancelled"],
                        "Contacted": ["Accepted",  "Cancelled"],
                        "Accepted":  ["Completed", "Cancelled"],
                        "Completed": [],
                        "Cancelled": [],
                    }
                    allowed = TRANSITIONS.get(ms, [])
                    if allowed:
                        new_status = st.selectbox(
                            "Move to Status",
                            allowed,
                            key=f"admin_m_sel_{real_idx}",
                        )
                        if st.button(
                            f"→ Set {new_status}",
                            key=f"admin_m_upd_{real_idx}",
                            use_container_width=True,
                            type="primary",
                        ):
                            update_match_status(real_idx, new_status, notes)
                            st.success(f"Match status updated to **{new_status}**.")
                            st.rerun()
                    else:
                        st.caption("No further transitions available.")

    st.divider()
    # ── Full match table ──────────────────────────────────────────────────────
    with st.expander("📄 Full Matches Table"):
        rows = []
        for m in matches:
            d = donor_map.get(m["donor_id"], {})
            r = req_map.get(m["req_id"],   {})
            rows.append({
                "Time":         m.get("matched_at", "—"),
                "Patient":      r.get("patient_name", m["req_id"]),
                "Donor":        d.get("name",  m["donor_id"]),
                "Blood Type":   d.get("blood_type", "—"),
                "City":         r.get("city", "—"),
                "Hospital":     r.get("hospital", "—"),
                "Match Status": m.get("match_status", "Pending"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TOP-LEVEL ADMIN PORTAL RENDER
# ─────────────────────────────────────────────────────────────────────────────

# ── If not logged in, show login screen ──────────────────────────────────────
if not st.session_state.get("admin_logged_in", False):
    _show_login()
    st.stop()

# ── Logged-in header ─────────────────────────────────────────────────────────
header_col, logout_col = st.columns([5, 1])
with header_col:
    st.title("🛡️ LifeLink Admin Portal")
    st.caption("Administrative control panel — manage donors, requests, and matches.")
with logout_col:
    st.write("")  # spacing
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.admin_logged_in = False
        st.success("Logged out successfully.")
        st.rerun()

st.divider()

# ── Admin navigation tabs ─────────────────────────────────────────────────────
tab_dash, tab_donors, tab_requests, tab_matches = st.tabs([
    "📊 Dashboard",
    "🩸 Donor Management",
    "📋 Request Management",
    "🤝 Match Management",
])

with tab_dash:
    _show_dashboard()

with tab_donors:
    _show_donor_management()

with tab_requests:
    _show_request_management()

with tab_matches:
    _show_match_management()
