"""
Lightweight in-session data store for donors, requests, and matches.
Uses st.session_state as the single source of truth; no external DB needed.
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

ORGAN_TYPES = ["Kidney", "Liver", "Heart", "Lung", "Pancreas", "Cornea", "Bone Marrow"]
DONATION_TYPES = ["Blood", "Organ", "Both"]

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


# ── CRUD helpers ──────────────────────────────────────────────────────────────
def add_donor(donor: dict) -> str:
    donor_id = str(uuid.uuid4())[:8].upper()
    donor["id"] = donor_id
    donor["registered_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    donor["status"] = "Available"
    st.session_state.donors.append(donor)
    return donor_id


def add_request(req: dict) -> str:
    req_id = str(uuid.uuid4())[:8].upper()
    req["id"] = req_id
    req["posted_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    req["status"] = "Open"
    st.session_state.requests.append(req)
    return req_id


def find_matches(req: dict) -> list[dict]:
    """
    Return donors compatible with the given request, sorted by city proximity
    (same city first), then by blood type (exact first, then universal donor).
    """
    results = []
    req_type = req["donation_type"]
    req_blood = req["blood_type"]
    req_city = req["city"]

    compatible_bloods = BLOOD_COMPATIBILITY.get(req_blood, [req_blood])

    for donor in st.session_state.donors:
        if donor["status"] != "Available":
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
            req_organs = set(req.get("organs", []))
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
    st.session_state.matches.append({
        "req_id": req_id,
        "donor_id": donor_id,
        "matched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    # Mark donor as Pledged
    for d in st.session_state.donors:
        if d["id"] == donor_id:
            d["status"] = "Pledged"
    # Mark request as Matched
    for r in st.session_state.requests:
        if r["id"] == req_id:
            r["status"] = "Matched"


# ── Seed data ─────────────────────────────────────────────────────────────────
def _seed_donors() -> list[dict]:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return [
        {"id": "SEED0001", "name": "Arjun Sharma",    "age": 28, "blood_type": "O+",  "city": "Mumbai",    "donation_type": "Blood",  "organs": [],                        "phone": "9876543210", "registered_at": now, "status": "Available"},
        {"id": "SEED0002", "name": "Priya Nair",      "age": 34, "blood_type": "A-",  "city": "Delhi",     "donation_type": "Both",   "organs": ["Kidney", "Cornea"],       "phone": "9876543211", "registered_at": now, "status": "Available"},
        {"id": "SEED0003", "name": "Rahul Verma",     "age": 45, "blood_type": "B+",  "city": "Bangalore", "donation_type": "Organ",  "organs": ["Liver", "Kidney"],        "phone": "9876543212", "registered_at": now, "status": "Available"},
        {"id": "SEED0004", "name": "Sunita Patel",    "age": 30, "blood_type": "AB+", "city": "Hyderabad", "donation_type": "Blood",  "organs": [],                         "phone": "9876543213", "registered_at": now, "status": "Available"},
        {"id": "SEED0005", "name": "Vikram Singh",    "age": 38, "blood_type": "O-",  "city": "Mumbai",    "donation_type": "Both",   "organs": ["Heart", "Lung", "Kidney"], "phone": "9876543214", "registered_at": now, "status": "Available"},
        {"id": "SEED0006", "name": "Deepa Menon",     "age": 26, "blood_type": "A+",  "city": "Chennai",   "donation_type": "Blood",  "organs": [],                         "phone": "9876543215", "registered_at": now, "status": "Available"},
        {"id": "SEED0007", "name": "Amit Joshi",      "age": 52, "blood_type": "B-",  "city": "Pune",      "donation_type": "Organ",  "organs": ["Cornea", "Bone Marrow"],  "phone": "9876543216", "registered_at": now, "status": "Available"},
        {"id": "SEED0008", "name": "Kavitha Reddy",   "age": 41, "blood_type": "O+",  "city": "Bangalore", "donation_type": "Blood",  "organs": [],                         "phone": "9876543217", "registered_at": now, "status": "Available"},
    ]


def _seed_requests() -> list[dict]:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return [
        {"id": "REQ00001", "patient_name": "Ravi Kumar",   "blood_type": "O+",  "city": "Mumbai",    "donation_type": "Blood",  "organs": [],           "urgency": "Critical", "hospital": "Lilavati Hospital",          "posted_at": now, "status": "Open"},
        {"id": "REQ00002", "patient_name": "Meena Devi",   "blood_type": "A-",  "city": "Delhi",     "donation_type": "Organ",  "organs": ["Kidney"],   "urgency": "High",     "hospital": "AIIMS Delhi",                "posted_at": now, "status": "Open"},
        {"id": "REQ00003", "patient_name": "Suresh Babu",  "blood_type": "B+",  "city": "Hyderabad", "donation_type": "Blood",  "organs": [],           "urgency": "Moderate", "hospital": "Apollo Hospitals",           "posted_at": now, "status": "Open"},
    ]
