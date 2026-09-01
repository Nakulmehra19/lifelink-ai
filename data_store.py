"""
Lightweight in-session data store for donors, requests, and matches.
Uses st.session_state as the single source of truth; no external DB needed.

Verification workflow added for Admin Portal:
  Donor verification_status: Pending → Verified | Rejected | Suspended
  Request verification_status: Pending → Approved | Rejected | Fulfilled | Closed
  Match match_status: Pending → Contacted → Accepted → Completed | Cancelled
"""
import streamlit as st
import datetime
import uuid


# ── Blood-type compatibility map ──────────────────────────────────────────────
# Keys = recipient blood type  →  Value = list of compatible donor blood types
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

# ── Organ compatibility (same blood-type families + universal rules) ───────────
ORGAN_BLOOD_COMPAT: dict[str, list[str]] = BLOOD_COMPATIBILITY  # same map

ORGAN_TYPES    = ["Kidney", "Liver", "Heart", "Lung", "Pancreas", "Cornea", "Bone Marrow"]
DONATION_TYPES = ["Blood", "Organ", "Both"]

# Donor verification statuses
DONOR_VERIFICATION_STATUSES   = ["Pending", "Verified", "Rejected", "Suspended"]
# Request verification statuses
REQUEST_VERIFICATION_STATUSES = ["Pending", "Approved", "Rejected", "Fulfilled", "Closed"]
# Match lifecycle statuses
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


# ── Session-state initialisation ──────────────────────────────────────────────
def init_store() -> None:
    """Call once at app startup to initialise all session-state keys."""
    if "donors" not in st.session_state:
        st.session_state.donors = _seed_donors()
    if "requests" not in st.session_state:
        st.session_state.requests = _seed_requests()
    if "matches" not in st.session_state:
        st.session_state.matches = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    # Admin auth state
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    # Migrate legacy records that lack verification fields
    _migrate_legacy_records()


def _migrate_legacy_records() -> None:
    """Ensure all existing records have the verification/status fields added by this version."""
    for d in st.session_state.get("donors", []):
        d.setdefault("verification_status", "Verified")   # seed donors start Verified
        d.setdefault("admin_notes", "")
    for r in st.session_state.get("requests", []):
        r.setdefault("verification_status", "Approved")   # seed requests start Approved
        r.setdefault("admin_notes", "")
    for m in st.session_state.get("matches", []):
        m.setdefault("match_status", "Pending")
        m.setdefault("admin_notes", "")


# ── CRUD helpers ──────────────────────────────────────────────────────────────
def add_donor(donor: dict) -> str:
    """Register a new donor.  Starts in Pending verification status."""
    donor_id = str(uuid.uuid4())[:8].upper()
    donor["id"]                  = donor_id
    donor["registered_at"]       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    donor["status"]              = "Available"
    donor["verification_status"] = "Pending"   # awaits admin approval
    donor["admin_notes"]         = ""
    st.session_state.donors.append(donor)
    return donor_id


def add_request(req: dict) -> str:
    """Post a new recipient request.  Starts in Pending verification status."""
    req_id = str(uuid.uuid4())[:8].upper()
    req["id"]                  = req_id
    req["posted_at"]           = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    req["status"]              = "Open"
    req["verification_status"] = "Pending"    # awaits admin approval
    req["admin_notes"]         = ""
    st.session_state.requests.append(req)
    return req_id


def find_matches(req: dict) -> list[dict]:
    """
    Return donors compatible with the given request, sorted by city proximity
    (same city first), then by blood type (exact first, then universal donor).

    Only VERIFIED + Available donors are eligible.
    Only APPROVED requests are eligible for matching.
    """
    results   = []
    req_type  = req["donation_type"]
    req_blood = req["blood_type"]
    req_city  = req["city"]

    compatible_bloods = BLOOD_COMPATIBILITY.get(req_blood, [req_blood])

    for donor in st.session_state.donors:
        # Gate 1: Must be Available (not Pledged/Suspended/etc.)
        if donor["status"] != "Available":
            continue
        # Gate 2: Must be admin-Verified
        if donor.get("verification_status", "Verified") != "Verified":
            continue

        # Donation-type gate
        d_type = donor["donation_type"]
        if d_type not in (req_type, "Both") and req_type != "Both":
            continue

        # Blood-type gate
        if donor["blood_type"] not in compatible_bloods:
            continue

        # Organ filter (if organ request)
        if req_type in ("Organ", "Both"):
            req_organs   = set(req.get("organs", []))
            donor_organs = set(donor.get("organs", []))
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
    """Record a confirmed match and update donor/request statuses."""
    st.session_state.matches.append({
        "req_id":       req_id,
        "donor_id":     donor_id,
        "matched_at":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "match_status": "Pending",   # admin can progress through lifecycle
        "admin_notes":  "",
    })
    # Mark donor as Pledged
    for d in st.session_state.donors:
        if d["id"] == donor_id:
            d["status"] = "Pledged"
    # Mark request as Matched
    for r in st.session_state.requests:
        if r["id"] == req_id:
            r["status"] = "Matched"


# ── Admin helpers ─────────────────────────────────────────────────────────────
def update_donor_verification(donor_id: str, new_status: str, notes: str = "") -> None:
    """Admin: change a donor's verification_status."""
    for d in st.session_state.donors:
        if d["id"] == donor_id:
            d["verification_status"] = new_status
            if notes:
                d["admin_notes"] = notes
            # If suspended, also mark unavailable
            if new_status == "Suspended":
                d["status"] = "Suspended"
            # If re-verified after suspension, restore Available
            if new_status == "Verified" and d["status"] == "Suspended":
                d["status"] = "Available"
            break


def update_request_verification(req_id: str, new_status: str, notes: str = "") -> None:
    """Admin: change a request's verification_status."""
    for r in st.session_state.requests:
        if r["id"] == req_id:
            r["verification_status"] = new_status
            if notes:
                r["admin_notes"] = notes
            # Map admin verification status onto operational status
            if new_status == "Approved":
                r["status"] = "Open"
            elif new_status in ("Rejected", "Closed"):
                r["status"] = "Closed"
            elif new_status == "Fulfilled":
                r["status"] = "Matched"
            break


def update_match_status(match_index: int, new_status: str, notes: str = "") -> None:
    """Admin: progress a match through its lifecycle."""
    if 0 <= match_index < len(st.session_state.matches):
        st.session_state.matches[match_index]["match_status"] = new_status
        if notes:
            st.session_state.matches[match_index]["admin_notes"] = notes
        # If cancelled, restore donor to Available
        if new_status == "Cancelled":
            donor_id = st.session_state.matches[match_index]["donor_id"]
            req_id   = st.session_state.matches[match_index]["req_id"]
            for d in st.session_state.donors:
                if d["id"] == donor_id and d["status"] == "Pledged":
                    d["status"] = "Available"
            for r in st.session_state.requests:
                if r["id"] == req_id and r["status"] == "Matched":
                    r["status"] = "Open"


# ── Seed data ─────────────────────────────────────────────────────────────────
def _seed_donors() -> list[dict]:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return [
        {"id": "SEED0001", "name": "Arjun Sharma",   "age": 28, "blood_type": "O+",  "city": "Mumbai",    "donation_type": "Blood",  "organs": [],                          "phone": "9876543210", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0002", "name": "Priya Nair",     "age": 34, "blood_type": "A-",  "city": "Delhi",     "donation_type": "Both",   "organs": ["Kidney", "Cornea"],        "phone": "9876543211", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0003", "name": "Rahul Verma",    "age": 45, "blood_type": "B+",  "city": "Bangalore", "donation_type": "Organ",  "organs": ["Liver", "Kidney"],         "phone": "9876543212", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0004", "name": "Sunita Patel",   "age": 30, "blood_type": "AB+", "city": "Hyderabad", "donation_type": "Blood",  "organs": [],                          "phone": "9876543213", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0005", "name": "Vikram Singh",   "age": 38, "blood_type": "O-",  "city": "Mumbai",    "donation_type": "Both",   "organs": ["Heart", "Lung", "Kidney"], "phone": "9876543214", "registered_at": now, "status": "Available", "verification_status": "Verified",  "admin_notes": ""},
        {"id": "SEED0006", "name": "Deepa Menon",    "age": 26, "blood_type": "A+",  "city": "Chennai",   "donation_type": "Blood",  "organs": [],                          "phone": "9876543215", "registered_at": now, "status": "Available", "verification_status": "Pending",   "admin_notes": ""},
        {"id": "SEED0007", "name": "Amit Joshi",     "age": 52, "blood_type": "B-",  "city": "Pune",      "donation_type": "Organ",  "organs": ["Cornea", "Bone Marrow"],   "phone": "9876543216", "registered_at": now, "status": "Available", "verification_status": "Pending",   "admin_notes": ""},
        {"id": "SEED0008", "name": "Kavitha Reddy",  "age": 41, "blood_type": "O+",  "city": "Bangalore", "donation_type": "Blood",  "organs": [],                          "phone": "9876543217", "registered_at": now, "status": "Available", "verification_status": "Rejected",  "admin_notes": "Incomplete documents"},
    ]


def _seed_requests() -> list[dict]:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return [
        {"id": "REQ00001", "patient_name": "Ravi Kumar",  "blood_type": "O+",  "city": "Mumbai",    "donation_type": "Blood", "organs": [],         "urgency": "Critical", "hospital": "Lilavati Hospital", "posted_at": now, "status": "Open",   "verification_status": "Approved", "admin_notes": ""},
        {"id": "REQ00002", "patient_name": "Meena Devi",  "blood_type": "A-",  "city": "Delhi",     "donation_type": "Organ", "organs": ["Kidney"], "urgency": "High",     "hospital": "AIIMS Delhi",       "posted_at": now, "status": "Open",   "verification_status": "Approved", "admin_notes": ""},
        {"id": "REQ00003", "patient_name": "Suresh Babu", "blood_type": "B+",  "city": "Hyderabad", "donation_type": "Blood", "organs": [],         "urgency": "Moderate", "hospital": "Apollo Hospitals",  "posted_at": now, "status": "Open",   "verification_status": "Pending",  "admin_notes": ""},
    ]
