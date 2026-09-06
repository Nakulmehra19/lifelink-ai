"""
LifeLink — Persistent data store backed by Supabase / PostgreSQL.

Supabase is the single source of truth for all donors, requests, matches,
and activity logs.  st.session_state holds a per-session read-cache only;
every mutation writes to the DB first, then refreshes the cache.

Public API (unchanged from the original session-state version):
    init_store()
    add_donor(donor)          → str (donor_id)
    add_request(req)          → str (req_id)
    find_matches(req)         → list[dict]
    record_match(req_id, donor_id)
    update_donor_verification(donor_id, new_status, notes="")
    update_request_verification(req_id, new_status, notes="")
    update_match_status(match_index, new_status, notes="")
    clear_donors()
    clear_requests()
    clear_matches()
    reset_all()

Verification workflow:
    Donor  verification_status : Pending → Verified | Rejected | Suspended
    Request verification_status: Pending → Approved | Rejected | Fulfilled | Closed
    Match  match_status        : Pending → Contacted → Accepted → Completed | Cancelled
"""
import datetime
import uuid

import streamlit as st
from supabase import create_client, Client


# ── Blood-type compatibility map ──────────────────────────────────────────────
BLOOD_COMPATIBILITY: dict[str, list[str]] = {
    "A+":  ["A+", "A-", "O+", "O-"],
    "A-":  ["A-", "O-"],
    "B+":  ["B+", "B-", "O+", "O-"],
    "B-":  ["B-", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+":  ["O+", "O-"],
    "O-":  ["O-"],
}

ALL_BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

ORGAN_BLOOD_COMPAT: dict[str, list[str]] = BLOOD_COMPATIBILITY

ORGAN_TYPES    = ["Kidney", "Liver", "Heart", "Lung", "Pancreas", "Cornea", "Bone Marrow"]
DONATION_TYPES = ["Blood", "Organ", "Both"]

DONOR_VERIFICATION_STATUSES   = ["Pending", "Verified", "Rejected", "Suspended"]
REQUEST_VERIFICATION_STATUSES = ["Pending", "Approved", "Rejected", "Fulfilled", "Closed"]
MATCH_STATUSES = ["Pending", "Contacted", "Accepted", "Completed", "Cancelled"]

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Ahmedabad",
    "Chennai", "Kolkata", "Pune", "Jaipur", "Lucknow",
    "Kanpur", "Nagpur", "Indore", "Bhopal", "Visakhapatnam",
    "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra",
    "Nashik", "Faridabad", "Meerut", "Rajkot", "Varanasi",
    "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Allahabad",
    "Ranchi", "Howrah", "Coimbatore", "Jabalpur", "Gwalior",
    "Vijayawada", "Jodhpur", "Madurai", "Raipur", "Kota",
]


# ── Supabase client ───────────────────────────────────────────────────────────

def _get_client() -> Client:
    """
    Return a cached Supabase client.
    The client object is stored in st.session_state so it is created at most
    once per browser session (Streamlit reuses the session across reruns).
    """
    if "_supabase_client" not in st.session_state:
        url: str = st.secrets["supabase"]["url"]
        key: str = st.secrets["supabase"]["key"]
        st.session_state._supabase_client = create_client(url, key)
    return st.session_state._supabase_client


# ── Session-state cache refresh ───────────────────────────────────────────────

def _refresh_session_state() -> None:
    """
    Pull the latest rows from Supabase and overwrite the three session-state
    lists that page views read directly.

    Called:
      - once per session on first load (inside init_store)
      - after every DB mutation (add / update / delete)

    After a successful fetch, sets _db_loaded=True so that init_store()
    skips further Supabase reads on subsequent reruns within the same session
    that have no mutations.
    """
    client = _get_client()
    try:
        donors_res   = client.table("donors").select("*").execute()
        requests_res = client.table("requests").select("*").execute()
        matches_res  = client.table("matches").select("*").execute()

        st.session_state.donors   = donors_res.data   or []
        st.session_state.requests = requests_res.data or []
        st.session_state.matches  = matches_res.data  or []
        # Mark cache as fresh — init_store() will skip DB reads on next reruns.
        st.session_state._db_loaded = True
    except Exception as exc:
        st.error(f"⚠️ Could not refresh data from Supabase: {exc}")


# ── Activity log ──────────────────────────────────────────────────────────────

def _log(event_type: str, entity_id: str = "", description: str = "") -> None:
    """Insert a row into the activity_log table (best-effort; never raises)."""
    try:
        _get_client().table("activity_log").insert({
            "event_type":  event_type,
            "entity_id":   entity_id,
            "description": description,
        }).execute()
    except Exception:
        pass  # logging failure must never break the main flow


# ── Session-state initialisation ──────────────────────────────────────────────

def init_store() -> None:
    """
    Called on every Streamlit rerun by app.py.

    Strategy:
      - Ephemeral keys (admin auth, chat history) are initialised once per
        browser session and never touched again by this function.
      - DB seeding is checked at most once per browser session (_db_seeded flag).
      - The full Supabase SELECT (donors / requests / matches) is performed
        only when _db_loaded is False — i.e. on the very first rerun of a
        session, or immediately after a mutation has cleared the flag via
        _refresh_session_state().
      - Every subsequent rerun (form typing, widget interactions, navigation)
        that has no DB write skips all Supabase network calls entirely,
        eliminating the visible loading delay.
    """
    # ── Ephemeral per-session keys (never persisted to DB) ────────────────
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ── Ensure lists exist even before the first DB fetch ─────────────────
    for key in ("donors", "requests", "matches"):
        if key not in st.session_state:
            st.session_state[key] = []

    # ── Fast path: cache already loaded, no DB calls needed this rerun ────
    if st.session_state.get("_db_loaded", False):
        return

    # ── Slow path: first rerun of this session (or post-mutation refresh) ─
    try:
        client = _get_client()
        # Seed check: run at most once per browser session.
        if not st.session_state.get("_db_seeded", False):
            count_res = client.table("donors").select("id", count="exact").execute()
            if (count_res.count or 0) == 0:
                _seed_db(client)
            st.session_state._db_seeded = True
    except Exception as exc:
        st.error(f"⚠️ Supabase connection failed: {exc}")
        return

    # ── Load donors / requests / matches into session-state cache ─────────
    _refresh_session_state()


def _seed_db(client: Client) -> None:
    """Insert seed donors and requests into the DB (called only when empty)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    seed_donors = [
        {"id": "SEED0001", "name": "Arjun Sharma",  "age": 28, "blood_type": "O+",  "city": "Mumbai",    "donation_type": "Blood",  "organs": [],                          "phone": "9876543210", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0002", "name": "Priya Nair",    "age": 34, "blood_type": "A-",  "city": "Delhi",     "donation_type": "Both",   "organs": ["Kidney", "Cornea"],        "phone": "9876543211", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0003", "name": "Rahul Verma",   "age": 45, "blood_type": "B+",  "city": "Bangalore", "donation_type": "Organ",  "organs": ["Liver", "Kidney"],         "phone": "9876543212", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0004", "name": "Sunita Patel",  "age": 30, "blood_type": "AB+", "city": "Hyderabad", "donation_type": "Blood",  "organs": [],                          "phone": "9876543213", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0005", "name": "Vikram Singh",  "age": 38, "blood_type": "O-",  "city": "Mumbai",    "donation_type": "Both",   "organs": ["Heart", "Lung", "Kidney"], "phone": "9876543214", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0006", "name": "Deepa Menon",   "age": 26, "blood_type": "A+",  "city": "Chennai",   "donation_type": "Blood",  "organs": [],                          "phone": "9876543215", "registered_at": now, "status": "Available", "verification_status": "Pending",   "admin_notes": ""},
        {"id": "SEED0007", "name": "Amit Joshi",    "age": 52, "blood_type": "B-",  "city": "Pune",      "donation_type": "Organ",  "organs": ["Cornea", "Bone Marrow"],   "phone": "9876543216", "registered_at": now, "status": "Available", "verification_status": "Pending",   "admin_notes": ""},
        {"id": "SEED0008", "name": "Kavitha Reddy", "age": 41, "blood_type": "O+",  "city": "Bangalore", "donation_type": "Blood",  "organs": [],                          "phone": "9876543217", "registered_at": now, "status": "Available", "verification_status": "Rejected",  "admin_notes": "Incomplete documents"},
    ]
    seed_requests = [
        {"id": "REQ00001", "patient_name": "Ravi Kumar",  "blood_type": "O+",  "city": "Mumbai",    "donation_type": "Blood", "organs": [],         "urgency": "Critical", "hospital": "Lilavati Hospital", "contact": "", "additional_info": "", "posted_at": now, "status": "Open",   "verification_status": "Approved", "admin_notes": ""},
        {"id": "REQ00002", "patient_name": "Meena Devi",  "blood_type": "A-",  "city": "Delhi",     "donation_type": "Organ", "organs": ["Kidney"], "urgency": "High",     "hospital": "AIIMS Delhi",       "contact": "", "additional_info": "", "posted_at": now, "status": "Open",   "verification_status": "Approved", "admin_notes": ""},
        {"id": "REQ00003", "patient_name": "Suresh Babu", "blood_type": "B+",  "city": "Hyderabad", "donation_type": "Blood", "organs": [],         "urgency": "Moderate", "hospital": "Apollo Hospitals",  "contact": "", "additional_info": "", "posted_at": now, "status": "Open",   "verification_status": "Pending",  "admin_notes": ""},
    ]

    # upsert so concurrent cold-starts never duplicate rows
    client.table("donors").upsert(seed_donors,   on_conflict="id").execute()
    client.table("requests").upsert(seed_requests, on_conflict="id").execute()
    _log("seed", "", "Database seeded with demo data")


# ── CRUD helpers ──────────────────────────────────────────────────────────────

def add_donor(donor: dict) -> str:
    """
    Register a new donor.
    Writes to Supabase first, then refreshes session-state cache.
    Returns the new donor ID.
    """
    donor_id = str(uuid.uuid4())[:8].upper()
    row = {
        "id":                  donor_id,
        "name":                donor.get("name", ""),
        "age":                 int(donor.get("age", 0)),
        "phone":               donor.get("phone", ""),
        "blood_type":          donor.get("blood_type", ""),
        "donation_type":       donor.get("donation_type", ""),
        "organs":              donor.get("organs", []),
        "city":                donor.get("city", ""),
        "status":              "Available",
        "verification_status": "Pending",
        "admin_notes":         "",
        "registered_at":       datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    try:
        _get_client().table("donors").insert(row).execute()
        _log("donor_added", donor_id, f"Donor '{row['name']}' registered from {row['city']}")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to register donor: {exc}")
    return donor_id


def add_request(req: dict) -> str:
    """
    Post a new recipient request.
    Writes to Supabase first, then refreshes session-state cache.
    Returns the new request ID.
    """
    req_id = str(uuid.uuid4())[:8].upper()
    row = {
        "id":                  req_id,
        "patient_name":        req.get("patient_name", ""),
        "hospital":            req.get("hospital", ""),
        "contact":             req.get("contact", ""),
        "blood_type":          req.get("blood_type", ""),
        "donation_type":       req.get("donation_type", ""),
        "organs":              req.get("organs", []),
        "urgency":             req.get("urgency", ""),
        "city":                req.get("city", ""),
        "additional_info":     req.get("additional_info", ""),
        "status":              "Open",
        "verification_status": "Pending",
        "admin_notes":         "",
        "posted_at":           datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    try:
        _get_client().table("requests").insert(row).execute()
        _log("request_added", req_id,
             f"Request by '{row['patient_name']}' at {row['hospital']}, {row['city']}")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to post request: {exc}")
    return req_id


def find_matches(req: dict) -> list[dict]:
    """
    Return donors compatible with the given request, sorted by city proximity
    (same city first) then by blood type (exact first).

    Reads from st.session_state.donors (already refreshed by init_store on
    this rerun).  Only Verified + Available donors are eligible.
    """
    results          = []
    req_type         = req["donation_type"]
    req_blood        = req["blood_type"]
    req_city         = req["city"]
    compatible_bloods = BLOOD_COMPATIBILITY.get(req_blood, [req_blood])

    for donor in st.session_state.donors:
        if donor["status"] != "Available":
            continue
        if donor.get("verification_status", "Verified") != "Verified":
            continue

        d_type = donor["donation_type"]
        if d_type not in (req_type, "Both") and req_type != "Both":
            continue

        if donor["blood_type"] not in compatible_bloods:
            continue

        if req_type in ("Organ", "Both"):
            req_organs   = set(req.get("organs") or [])
            donor_organs = set(donor.get("organs") or [])
            if req_organs and not req_organs.intersection(donor_organs):
                continue

        score = 0
        if donor["city"] == req_city:
            score += 10
        if donor["blood_type"] == req_blood:
            score += 5

        results.append({**donor, "_score": score})

    results.sort(key=lambda d: d["_score"], reverse=True)
    return results


def record_match(req_id: str, donor_id: str) -> None:
    """
    Record a confirmed donor-recipient match.
    Writes match row + updates donor and request rows in Supabase,
    then refreshes session-state cache.
    """
    client = _get_client()
    now    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        # 1. Insert match row
        client.table("matches").insert({
            "req_id":       req_id,
            "donor_id":     donor_id,
            "matched_at":   now,
            "match_status": "Pending",
            "admin_notes":  "",
        }).execute()

        # 2. Mark donor as Pledged
        client.table("donors").update({"status": "Pledged"}).eq("id", donor_id).execute()

        # 3. Mark request as Matched
        client.table("requests").update({"status": "Matched"}).eq("id", req_id).execute()

        _log("match_confirmed", req_id,
             f"Donor {donor_id} matched with request {req_id}")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to record match: {exc}")


# ── Admin helpers ─────────────────────────────────────────────────────────────

def update_donor_verification(donor_id: str, new_status: str, notes: str = "") -> None:
    """Admin: change a donor's verification_status. Writes to DB, then refreshes."""
    client = _get_client()
    update = {"verification_status": new_status}
    if notes:
        update["admin_notes"] = notes
    if new_status == "Suspended":
        update["status"] = "Suspended"
    # Re-verify after suspension → restore Available
    # We need the current status; read from session cache (already fresh)
    if new_status == "Verified":
        donor = next((d for d in st.session_state.donors if d["id"] == donor_id), None)
        if donor and donor.get("status") == "Suspended":
            update["status"] = "Available"
    try:
        client.table("donors").update(update).eq("id", donor_id).execute()
        _log("donor_verified", donor_id, f"Donor {donor_id} → {new_status}")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to update donor verification: {exc}")


def update_request_verification(req_id: str, new_status: str, notes: str = "") -> None:
    """Admin: change a request's verification_status. Writes to DB, then refreshes."""
    client = _get_client()
    update = {"verification_status": new_status}
    if notes:
        update["admin_notes"] = notes
    if new_status == "Approved":
        update["status"] = "Open"
    elif new_status in ("Rejected", "Closed"):
        update["status"] = "Closed"
    elif new_status == "Fulfilled":
        update["status"] = "Matched"
    try:
        client.table("requests").update(update).eq("id", req_id).execute()
        _log("request_verified", req_id, f"Request {req_id} → {new_status}")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to update request verification: {exc}")


def update_match_status(match_index: int, new_status: str, notes: str = "") -> None:
    """
    Admin: progress a match through its lifecycle.

    match_index is the positional index into st.session_state.matches
    (as used by the existing admin_portal.py enumerate() loop).
    Internally we resolve this to the match's DB serial `id` field.
    """
    matches = st.session_state.matches
    if not (0 <= match_index < len(matches)):
        return

    match_row = matches[match_index]
    db_id     = match_row.get("id")   # serial PK from Supabase SELECT
    if db_id is None:
        st.error("⚠️ Cannot update match: DB id missing from session cache.")
        return

    client = _get_client()
    update = {"match_status": new_status}
    if notes:
        update["admin_notes"] = notes

    try:
        client.table("matches").update(update).eq("id", db_id).execute()

        # If cancelled → restore donor to Available and request to Open
        if new_status == "Cancelled":
            donor_id = match_row.get("donor_id")
            req_id   = match_row.get("req_id")
            donor    = next((d for d in st.session_state.donors   if d["id"] == donor_id), None)
            req      = next((r for r in st.session_state.requests if r["id"] == req_id),   None)
            if donor and donor.get("status") == "Pledged":
                client.table("donors").update({"status": "Available"}).eq("id", donor_id).execute()
            if req and req.get("status") == "Matched":
                client.table("requests").update({"status": "Open"}).eq("id", req_id).execute()

        _log("match_status_updated", str(db_id),
             f"Match {db_id} (req {match_row.get('req_id')}) → {new_status}")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to update match status: {exc}")


# ── Data management helpers (used by settings.py) ─────────────────────────────

def delete_donor(donor_id: str) -> None:
    """
    Permanently delete a donor from Supabase.
    FK-safe order: related matches are deleted first (ON DELETE CASCADE handles
    this automatically, but we also delete explicitly to be safe), then the donor.
    Writes to DB first, then refreshes session-state cache.
    """
    try:
        client = _get_client()
        # Matches referencing this donor are cascade-deleted by the DB schema,
        # but also restore any matched requests to Open before removing.
        matches_res = client.table("matches").select("req_id").eq("donor_id", donor_id).execute()
        for m in (matches_res.data or []):
            client.table("requests").update({"status": "Open"}).eq("id", m["req_id"]).eq("status", "Matched").execute()
        # The ON DELETE CASCADE on matches.donor_id removes matches automatically.
        client.table("donors").delete().eq("id", donor_id).execute()
        _log("donor_deleted", donor_id, f"Donor {donor_id} permanently deleted by admin")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to delete donor: {exc}")


def delete_request(req_id: str) -> None:
    """
    Permanently delete a request from Supabase.
    FK-safe order: restore pledged donors from related matches to Available,
    then delete — matches cascade-delete automatically via DB schema.
    Writes to DB first, then refreshes session-state cache.
    """
    try:
        client = _get_client()
        # Restore any pledged donor linked to this request back to Available
        matches_res = client.table("matches").select("donor_id").eq("req_id", req_id).execute()
        for m in (matches_res.data or []):
            client.table("donors").update({"status": "Available"}).eq("id", m["donor_id"]).eq("status", "Pledged").execute()
        # ON DELETE CASCADE removes related matches automatically.
        client.table("requests").delete().eq("id", req_id).execute()
        _log("request_deleted", req_id, f"Request {req_id} permanently deleted by admin")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to delete request: {exc}")


def clear_matches() -> None:
    """Delete all matches from DB (FK-safe; no cascade needed here). Refresh cache."""
    try:
        # Delete all rows: Supabase requires a filter; use neq on serial id != 0
        _get_client().table("matches").delete().neq("id", 0).execute()
        _log("clear_matches", "", "All matches cleared by admin")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to clear matches: {exc}")


def clear_requests() -> None:
    """
    Delete all requests from DB.
    Matches reference requests via FK CASCADE, so matches are deleted first.
    """
    try:
        client = _get_client()
        client.table("matches").delete().neq("id", 0).execute()
        client.table("requests").delete().neq("id", "").execute()
        _log("clear_requests", "", "All requests (and dependent matches) cleared by admin")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to clear requests: {exc}")


def clear_donors() -> None:
    """
    Delete all donors from DB.
    FK order: matches → (requests are kept) → donors.
    """
    try:
        client = _get_client()
        client.table("matches").delete().neq("id", 0).execute()
        client.table("donors").delete().neq("id", "").execute()
        _log("clear_donors", "", "All donors (and dependent matches) cleared by admin")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to clear donors: {exc}")


def reset_all() -> None:
    """
    Full platform reset: delete all data in FK-safe order, re-seed the DB,
    and refresh session-state.  chat_history is cleared by the caller.
    """
    try:
        client = _get_client()
        client.table("matches").delete().neq("id", 0).execute()
        client.table("requests").delete().neq("id", "").execute()
        client.table("donors").delete().neq("id", "").execute()
        _seed_db(client)
        _log("reset_all", "", "Full platform reset to seed state")
        _refresh_session_state()
    except Exception as exc:
        st.error(f"⚠️ Failed to reset platform: {exc}")


# ── Legacy helpers kept for backward compatibility ────────────────────────────

def _migrate_legacy_records() -> None:
    """No-op: DB schema enforces all defaults; kept so any stale import doesn't break."""
    pass


def _seed_donors() -> list[dict]:
    """Return seed donor list (used only by reset_all via _seed_db)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return [
        {"id": "SEED0001", "name": "Arjun Sharma",  "age": 28, "blood_type": "O+",  "city": "Mumbai",    "donation_type": "Blood",  "organs": [],                          "phone": "9876543210", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0002", "name": "Priya Nair",    "age": 34, "blood_type": "A-",  "city": "Delhi",     "donation_type": "Both",   "organs": ["Kidney", "Cornea"],        "phone": "9876543211", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0003", "name": "Rahul Verma",   "age": 45, "blood_type": "B+",  "city": "Bangalore", "donation_type": "Organ",  "organs": ["Liver", "Kidney"],         "phone": "9876543212", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0004", "name": "Sunita Patel",  "age": 30, "blood_type": "AB+", "city": "Hyderabad", "donation_type": "Blood",  "organs": [],                          "phone": "9876543213", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0005", "name": "Vikram Singh",  "age": 38, "blood_type": "O-",  "city": "Mumbai",    "donation_type": "Both",   "organs": ["Heart", "Lung", "Kidney"], "phone": "9876543214", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0006", "name": "Deepa Menon",   "age": 26, "blood_type": "A+",  "city": "Chennai",   "donation_type": "Blood",  "organs": [],                          "phone": "9876543215", "registered_at": now, "status": "Available", "verification_status": "Pending",   "admin_notes": ""},
        {"id": "SEED0007", "name": "Amit Joshi",    "age": 52, "blood_type": "B-",  "city": "Pune",      "donation_type": "Organ",  "organs": ["Cornea", "Bone Marrow"],   "phone": "9876543216", "registered_at": now, "status": "Available", "verification_status": "Pending",   "admin_notes": ""},
        {"id": "SEED0008", "name": "Kavitha Reddy", "age": 41, "blood_type": "O+",  "city": "Bangalore", "donation_type": "Blood",  "organs": [],                          "phone": "9876543217", "registered_at": now, "status": "Available", "verification_status": "Rejected",  "admin_notes": "Incomplete documents"},
    ]


def _seed_requests() -> list[dict]:
    """Return seed request list (kept for API compatibility)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return [
        {"id": "REQ00001", "patient_name": "Ravi Kumar",  "blood_type": "O+",  "city": "Mumbai",    "donation_type": "Blood", "organs": [],         "urgency": "Critical", "hospital": "Lilavati Hospital", "contact": "", "additional_info": "", "posted_at": now, "status": "Open",   "verification_status": "Approved", "admin_notes": ""},
        {"id": "REQ00002", "patient_name": "Meena Devi",  "blood_type": "A-",  "city": "Delhi",     "donation_type": "Organ", "organs": ["Kidney"], "urgency": "High",     "hospital": "AIIMS Delhi",       "contact": "", "additional_info": "", "posted_at": now, "status": "Open",   "verification_status": "Approved", "admin_notes": ""},
        {"id": "REQ00003", "patient_name": "Suresh Babu", "blood_type": "B+",  "city": "Hyderabad", "donation_type": "Blood", "organs": [],         "urgency": "Moderate", "hospital": "Apollo Hospitals",  "contact": "", "additional_info": "", "posted_at": now, "status": "Open",   "verification_status": "Pending",  "admin_notes": ""},
    ]
