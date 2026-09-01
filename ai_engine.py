"""
AI assistant powered by Gemini 2.5 Flash (gemini-3.6-flash) via the google-genai SDK.
Provides donor-recipient guidance, compatibility explanations, and triage advice.
"""
from google import genai
from google.genai import types as genai_types


SYSTEM_PROMPT = """You are LifeLink AI, a compassionate and medically informed assistant for a blood and organ donation matching platform.

Your responsibilities:
1. Explain blood type compatibility clearly (e.g., why O- is a universal donor, what ABO/Rh factors mean).
2. Help donors understand what organ donation involves and how the matching process works.
3. Guide recipients or their families through posting urgent requests.
4. Provide empathetic support and triage guidance (always recommend contacting medical professionals for emergencies).
5. Answer general FAQs about donation registration, eligibility, and the platform.

Important rules:
- Never give specific medical diagnoses or treatment plans.
- Always recommend consulting a licensed physician for clinical decisions.
- Keep responses concise, warm, and easy to understand.
- When relevant, remind users that every donation can save up to 8 lives.
- If asked about a specific donor or patient, remind the user that personal data is confidential and to use the matching feature on the platform.
"""


def get_ai_client(api_key: str) -> genai.Client:
    """Return a configured Gemini client."""
    return genai.Client(api_key=api_key)


def ask_ai(client: genai.Client, history: list[dict], user_message: str) -> str:
    """
    Send a message to Gemini 2.5 Flash with full conversation history.
    Returns the model's text response.
    """
    # Build contents list from history + new user message
    contents = []
    for turn in history:
        role = turn["role"]   # "user" or "model"
        contents.append(
            genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=turn["text"])]
            )
        )
    # Append the new user turn
    contents.append(
        genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)]
        )
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=contents,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=1024,
        ),
    )
    return response.text or ""


def build_match_summary_prompt(request: dict, matches: list[dict]) -> str:
    """Build a prompt that asks Gemini to summarise and explain a match result."""
    req_desc = (
        f"Patient '{request['patient_name']}' at {request['hospital']}, {request['city']}. "
        f"Needs: {request['donation_type']} | Blood type: {request['blood_type']} | "
        f"Organs: {', '.join(request.get('organs', [])) or 'N/A'} | Urgency: {request['urgency']}."
    )
    if not matches:
        return (
            f"A request was posted: {req_desc} "
            "Unfortunately, no compatible donors were found in the system right now. "
            "Please explain why matches can be hard to find and suggest what the patient's family can do next."
        )

    top = matches[:3]
    donors_desc = "; ".join(
        f"{d['name']} (Blood: {d['blood_type']}, City: {d['city']}, "
        f"Donates: {d['donation_type']}, Organs: {', '.join(d.get('organs', [])) or 'N/A'})"
        for d in top
    )
    return (
        f"A request was posted: {req_desc} "
        f"The top compatible donors found are: {donors_desc}. "
        "Please write a short, warm summary (3-4 sentences) explaining why these donors are compatible, "
        "what happens next in the donation process, and an encouraging message for the family."
    )
