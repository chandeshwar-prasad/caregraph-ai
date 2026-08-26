from typing import List, Dict, Any, Tuple

# Pure Python deterministic red-flag keywords
RED_FLAG_PATTERNS = [
    "chest pain",
    "shortness of breath",
    "can't breathe",
    "cannot breathe",
    "difficulty breathing",
    "sudden numbness",
    "sudden weakness",
    "severe bleeding",
    "unconscious",
    "anaphylaxis",
    "loss of consciousness",
    "stroke symptoms",
    "slurred speech",
    "face drooping",
    "heart attack",
    "cardiac arrest",
    "stopped breathing",
    "not breathing",
]

URGENT_PATTERNS = [
    "high fever",
    "severe headache",
    "persistent vomiting",
    "spreading rash",
    "severe abdominal pain",
    "stiff neck"
]


def evaluate_red_flags(text: str) -> bool:
    """
    Pure Python deterministic evaluator checking for critical red-flag terms.
    Executes BEFORE LLM reasoning. Cannot be overridden by LLM output or prompt injections.
    """
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in RED_FLAG_PATTERNS)


def get_deterministic_emergency_response() -> str:
    """
    Returns PRD-grounded deterministic emergency escalation guidance.
    """
    return (
        "🚨 **EMERGENCY SAFETY ESCALATION DETECTED**\n\n"
        "Your symptoms indicate a potential medical emergency that requires immediate professional clinical evaluation.\n\n"
        "**Recommended Action:**\n"
        "• Contact your local emergency services (such as 911 / 112 / 102) immediately or go to the nearest emergency room.\n"
        "• Do not attempt self-treatment or delay emergency care.\n\n"
        "*Disclaimer: CareGraph AI is a care-coordination assistant, not an emergency medical service.*"
    )


def evaluate_triage_risk(text: str, entities: Dict[str, Any]) -> str:
    """
    Categorizes symptom severity into 'emergency', 'urgent', or 'non_urgent'.
    """
    if evaluate_red_flags(text):
        return "emergency"
    
    text_lower = text.lower()
    if any(pattern in text_lower for pattern in URGENT_PATTERNS):
        return "urgent"
        
    return "non_urgent"


def build_triage_response(
    user_msg: str,
    risk_level: str,
    knowledge_items: List[Dict[str, Any]]
) -> Tuple[str, List[str]]:
    """
    Drafts non-diagnostic care navigation response and suggests follow-up questions.
    Enforces strict disclaimers against diagnosis, prescriptions, and treatment plans.
    """
    if risk_level == "emergency":
        return get_deterministic_emergency_response(), []

    disclaimer = (
        "*(Note: I am a care-coordination assistant, not a doctor. I cannot provide clinical diagnoses, "
        "prescribe medications, or alter dosages. The following is general care navigation information.)*\n\n"
    )

    content_parts = [disclaimer]

    if risk_level == "urgent":
        content_parts.append(
            "⚠️ **Urgent Evaluation Advised:** Your reported symptoms warrant prompt evaluation by a healthcare provider (such as visiting an urgent care clinic or contacting your physician today).\n"
        )

    if knowledge_items:
        content_parts.append("**Care Navigation Guidance:**\n")
        for item in knowledge_items:
            content_parts.append(f"• {item['guidance']}\n")
    else:
        content_parts.append(
            "For your reported symptoms, please monitor your condition, rest, and stay hydrated. "
            "If symptoms worsen or persist, please consult a qualified healthcare professional.\n"
        )

    response_text = "\n".join(content_parts).strip()

    follow_up_questions = [
        "How long have you been experiencing these symptoms?",
        "Are your symptoms getting progressively worse or staying the same?",
        "Would you like me to help schedule an appointment with a healthcare provider?"
    ]

    return response_text, follow_up_questions
