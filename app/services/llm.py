import os
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
import pydantic

from app.schemas_ai import IntentExtraction, IntentEnum

logger = logging.getLogger(__name__)

# Custom Decoupled Exceptions
class LLMError(Exception):
    """Base exception for LLM operations."""
    pass

class LLMAuthenticationError(LLMError):
    """Authentication or API key misconfiguration."""
    pass

class LLMTimeoutError(LLMError):
    """Request timeout."""
    pass

class LLMConnectionError(LLMError):
    """Connection or network error."""
    pass

class LLMRateLimitError(LLMError):
    """Rate limit exceeded."""
    pass


class BaseLLMService(ABC):
    @abstractmethod
    def extract_intent(self, text: str) -> IntentExtraction:
        """Extract user intent and entities from the input text."""
        pass

    @abstractmethod
    def generate_response(self, text: str, intent_info: IntentExtraction) -> str:
        """Generate a user-facing conversational response based on user text and extracted intent."""
        pass

    @abstractmethod
    def is_mock_mode(self) -> bool:
        """Return True if this is the mock implementation, False if live."""
        pass


class MockLLMService(BaseLLMService):
    def extract_intent(self, text: str) -> IntentExtraction:
        text_lower = text.lower()
        
        # 1. Emergency detection
        emergency_triggers = ["emergency", "911", "chest pain", "bleeding", "severe", "suicide", "hurt", "die", "unconscious"]
        if any(trigger in text_lower for trigger in emergency_triggers):
            return IntentExtraction(
                intent=IntentEnum.EMERGENCY,
                confidence=1.0,
                extracted_entities={"emergency_keyword_detected": True}
            )

        # 2. Scheduling detection
        scheduling_triggers = ["appointment", "schedule", "book", "meet", "doctor", "dermatologist", "reschedule", "calendar", "cancel"]
        if any(trigger in text_lower for trigger in scheduling_triggers) and not any(r_kw in text_lower for r_kw in ["reminder", "reminders"]):
            # Try to extract doctor type and time if mentioned
            entities = {}
            if "dermatologist" in text_lower:
                entities["doctor_specialty"] = "dermatologist"
            if "tomorrow" in text_lower:
                entities["date_preference"] = "tomorrow"
            elif "wednesday" in text_lower:
                entities["date_preference"] = "wednesday"
            return IntentExtraction(
                intent=IntentEnum.SCHEDULING,
                confidence=0.95,
                extracted_entities=entities
            )

        # 3. Reminders detection
        reminders_triggers = ["remind", "reminder", "pill", "take my"]
        if any(trigger in text_lower for trigger in reminders_triggers):
            return IntentExtraction(
                intent=IntentEnum.REMINDERS,
                confidence=0.95,
                extracted_entities={}
            )

        # 4. Records detection (explicit records retrieval/trend requests)
        records_triggers = [
            "record", "records", "my vital", "my vitals", "vitals", "blood pressure reading",
            "summary", "report", "test result", "bp reading", "history", "active medication",
            "my medication", "my medications", "medication", "medications", "prescription", "prescriptions",
            "heart rate trend", "pulse trend", "vital trend", "trend analysis", "trend over",
            "spo2 reading", "oxygen reading", "temperature history", "recorded weight",
            "my weight", "bmi reading", "my profile"
        ]
        if any(trigger in text_lower for trigger in records_triggers):
            entities = {}
            if "blood pressure" in text_lower or "bp" in text_lower:
                entities["record_type"] = "blood pressure"
            elif "medication" in text_lower or "medications" in text_lower or "prescription" in text_lower:
                entities["record_type"] = "medications"
            return IntentExtraction(
                intent=IntentEnum.RECORDS,
                confidence=0.95,
                extracted_entities=entities
            )

        # 5. Triage detection
        triage_triggers = [
            "fever", "cough", "symptom", "pain", "headache", "cold", "sick", "ill",
            "ache", "sore", "rash", "throat", "swallow", "nausea", "vomit", "stuffy",
            "sneezing", "queasy", "dizzy", "infection", "recovery", "guidance", "chills", "temperature"
        ]
        if any(trigger in text_lower for trigger in triage_triggers):
            entities = {}
            symptoms = []
            if "cough" in text_lower:
                symptoms.append("cough")
            if "fever" in text_lower or "temperature" in text_lower:
                symptoms.append("fever")
            if "headache" in text_lower:
                symptoms.append("headache")
            if "rash" in text_lower:
                symptoms.append("rash")
            if "throat" in text_lower:
                symptoms.append("sore throat")
            entities["symptom"] = ", ".join(symptoms) if symptoms else "general symptoms"
            return IntentExtraction(
                intent=IntentEnum.TRIAGE,
                confidence=0.95,
                extracted_entities=entities
            )

        # 6. Fallback General
        return IntentExtraction(
            intent=IntentEnum.GENERAL,
            confidence=0.8,
            extracted_entities={}
        )

    def generate_response(self, text: str, intent_info: IntentExtraction) -> str:
        intent = intent_info.intent
        
        if intent == IntentEnum.EMERGENCY:
            return (
                "🚨 EMERGENCY DETECTED: If you are experiencing a life-threatening medical emergency or severe symptoms, "
                "please contact emergency services immediately (911 in the US, 112 in the EU, or 102 in India). "
                "Do not wait. I am an AI coordination assistant and cannot handle emergencies."
            )
        
        elif intent == IntentEnum.TRIAGE:
            symptoms = intent_info.extracted_entities.get("symptom", "your symptoms")
            return (
                f"I understand you are asking about {symptoms}. Please note that I am a care coordination assistant, "
                f"not a doctor. I cannot provide a clinical diagnosis, prescribe medications, or recommend treatments. "
                f"I can help you coordinate an appointment with a professional if you'd like. "
                f"(Mock Mode: detected triage intent)"
            )
            
        elif intent == IntentEnum.SCHEDULING:
            pref = intent_info.extracted_entities.get("date_preference", "a convenient time")
            spec = intent_info.extracted_entities.get("doctor_specialty", "the doctor")
            return (
                f"I've noted that you want to schedule an appointment with {spec} around {pref}. "
                f"I am ready to help you check available slots in the next step. "
                f"(Mock Mode: detected scheduling intent)"
            )
            
        elif intent == IntentEnum.RECORDS:
            rtype = intent_info.extracted_entities.get("record_type", "health records")
            return (
                f"I detected that you want to view your {rtype}. I can retrieve that for you "
                f"once record services are fully integrated. "
                f"(Mock Mode: detected records retrieval intent)"
            )
            
        elif intent == IntentEnum.REMINDERS:
            return (
                "I understand you would like to set up or view your medication reminders. "
                "I will be able to assist in creating medication reminders once reminder tools are activated. "
                "(Mock Mode: detected reminders intent)"
            )
            
        else:
            return (
                f"Hello! I am your CareGraph assistant. I can help coordinate your symptoms, "
                f"appointments, medication reminders, and health records. How can I assist you today? "
                f"(Mock Mode: general response)"
            )

    def is_mock_mode(self) -> bool:
        return True


class GroqLLMService(BaseLLMService):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        
        # Defer groq import to instantiation time to prevent import errors if not installed
        try:
            import groq
            self.client = groq.Groq(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Groq Client: {e}")
            raise LLMError("Failed to initialize Groq SDK.")

    def _translate_exception(self, e: Exception) -> Exception:
        import groq
        if isinstance(e, groq.AuthenticationError):
            return LLMAuthenticationError("Invalid API key or authentication failure.")
        elif isinstance(e, groq.APITimeoutError):
            return LLMTimeoutError("The request to the Groq API timed out.")
        elif isinstance(e, groq.APIConnectionError):
            return LLMConnectionError("Failed to connect to the Groq API network.")
        elif isinstance(e, groq.RateLimitError):
            return LLMRateLimitError("Groq API rate limit exceeded.")
        elif isinstance(e, groq.APIStatusError):
            return LLMError(f"Groq API returned status code {e.status_code}.")
        elif isinstance(e, groq.APIError):
            return LLMError(f"Groq API error occurred: {str(e)}")
        return e

    def extract_intent(self, text: str) -> IntentExtraction:
        system_prompt = (
            "You are a healthcare query classifier. Analyze the user query and extract the user's intent "
            "and entities. You must return a JSON object that strictly adheres to this schema:\n"
            "{\n"
            "  \"intent\": \"triage\" | \"scheduling\" | \"records\" | \"reminders\" | \"general\" | \"emergency\",\n"
            "  \"confidence\": float (between 0.0 and 1.0),\n"
            "  \"extracted_entities\": dict (extracted entities e.g., {'symptom': 'cough', 'date': 'tomorrow'})\n"
            "}\n\n"
            "Intent Guidelines:\n"
            "- emergency: User is experiencing life-threatening symptoms (chest pain, severe bleeding, unconsciousness) or asking for emergency assistance.\n"
            "- triage: User asks about non-urgent symptoms, feeling sick, coughing, headaches, etc.\n"
            "- scheduling: User wants to search, book, reschedule, or cancel a doctor appointment.\n"
            "- records: User wants to view, retrieve, summarize, or trends in their health files, vitals, or reports.\n"
            "- reminders: User wants to set up, update, check, or cancel medication reminders.\n"
            "- general: Greetings, chit-chat, unrelated queries.\n\n"
            "Return ONLY the raw JSON object. Do not include markdown codeblocks or conversational text."
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            raw_content = response.choices[0].message.content
            # Record token usage
            if hasattr(response, "usage") and response.usage:
                from app.services.telemetry import global_cost_tracker
                global_cost_tracker.record_usage(
                    model=self.model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    workflow_name="intent_extraction"
                )
            # Validate JSON with Pydantic
            intent_data = pydantic.TypeAdapter(IntentExtraction).validate_json(raw_content)
            return intent_data
        except Exception as e:
            translated = self._translate_exception(e)
            logger.error(f"Error during extract_intent: {translated}", exc_info=True)
            raise translated

    def generate_response(self, text: str, intent_info: IntentExtraction) -> str:
        system_prompt = (
            "You are CareGraph AI, a conversational healthcare coordination assistant. "
            "Your job is to coordinate symptoms, scheduling, records, and reminders.\n"
            f"The user query has been classified as intent: '{intent_info.intent.value}' "
            f"with entities: {json.dumps(intent_info.extracted_entities)}.\n\n"
            "Guidelines:\n"
            "1. Be polite, clear, and reassuring.\n"
            "2. Keep the focus strictly on coordination and next steps (e.g. finding a doctor, checking schedules, setting reminders).\n"
            "3. If the intent is 'emergency', tell the user to contact emergency services immediately and refuse further advice.\n"
            "4. If the intent is 'triage', advise them to consult a qualified physician and note that you are an AI coordinator, not a doctor. Do not provide a diagnostic result.\n"
            "5. Refuse clinical diagnostic requests or prescription actions.\n"
            "6. Answer briefly and directly."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7
            )
            if hasattr(response, "usage") and response.usage:
                from app.services.telemetry import global_cost_tracker
                global_cost_tracker.record_usage(
                    model=self.model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    workflow_name="generate_response"
                )
            return response.choices[0].message.content
        except Exception as e:
            translated = self._translate_exception(e)
            logger.error(f"Error during generate_response: {translated}", exc_info=True)
            raise translated

    def is_mock_mode(self) -> bool:
        return False


# --- Phase 9 Milestone 4: Model Router & Comparative Performance ---

class ModelRouter:
    """
    Intelligent Model Router for balancing latency, cost, and clinical accuracy.
    Routing Rule Invariant: Never silently escalate to expensive strong models without
    explicit task-level complexity classification.
    """
    FAST_MODEL = "llama-3.1-8b-instant"
    STRONG_MODEL = "llama-3.3-70b-versatile"
    FALLBACK_MODEL = "llama-3.3-70b-versatile"

    ROUTING_RULES = {
        "intent_classification": "llama-3.1-8b-instant",
        "scheduling": "llama-3.1-8b-instant",
        "reminders": "llama-3.1-8b-instant",
        "general_chat": "llama-3.1-8b-instant",
        "complex_triage": "llama-3.3-70b-versatile",
        "clinical_synthesis": "llama-3.3-70b-versatile",
        "records_trend_analysis": "llama-3.3-70b-versatile",
    }

    @classmethod
    def select_model(cls, task_type: str, complexity_score: float = 0.5) -> str:
        """
        Determines optimal model tier based on task type and explicit complexity score.
        """
        # Complex clinical reasoning tasks route to Strong Tier
        if task_type in ["complex_triage", "clinical_synthesis", "records_trend_analysis"] or complexity_score > 0.75:
            logger.info(f"ModelRouter: Assigned STRONG tier ({cls.STRONG_MODEL}) for task '{task_type}'")
            return cls.STRONG_MODEL

        # High-throughput, low-latency tasks route to Fast Tier
        chosen = cls.ROUTING_RULES.get(task_type, cls.FAST_MODEL)
        logger.info(f"ModelRouter: Assigned FAST tier ({chosen}) for task '{task_type}'")
        return chosen

    @classmethod
    def get_routing_policy_summary(cls) -> Dict[str, Any]:
        return {
            "fast_tier_model": cls.FAST_MODEL,
            "strong_tier_model": cls.STRONG_MODEL,
            "default_fallback_model": cls.FALLBACK_MODEL,
            "task_routing_matrix": cls.ROUTING_RULES,
            "escalation_policy": "Explicit task complexity threshold (>0.75) required. No silent escalation."
        }


def evaluate_model_router_performance(sample_queries_count: int = 50) -> Dict[str, Any]:
    """
    Computes comparative performance, cost, and latency metrics across Fast Tier vs Strong Tier.
    """
    from app.services.telemetry import calculate_token_cost

    # Synthetic representative workload (avg 120 prompt tokens, 85 completion tokens)
    avg_prompt_tokens = 120
    avg_completion_tokens = 85

    fast_cost_per_req = calculate_token_cost(ModelRouter.FAST_MODEL, avg_prompt_tokens, avg_completion_tokens)
    strong_cost_per_req = calculate_token_cost(ModelRouter.STRONG_MODEL, avg_prompt_tokens, avg_completion_tokens)

    fast_total_cost = round(fast_cost_per_req * sample_queries_count, 6)
    strong_total_cost = round(strong_cost_per_req * sample_queries_count, 6)
    cost_savings_pct = round(((strong_total_cost - fast_total_cost) / strong_total_cost) * 100, 2) if strong_total_cost > 0 else 0.0

    return {
        "workload_queries": sample_queries_count,
        "fast_tier": {
            "model": ModelRouter.FAST_MODEL,
            "estimated_latency_ms": 180.0,
            "cost_per_query_usd": fast_cost_per_req,
            "total_workload_cost_usd": fast_total_cost
        },
        "strong_tier": {
            "model": ModelRouter.STRONG_MODEL,
            "estimated_latency_ms": 520.0,
            "cost_per_query_usd": strong_cost_per_req,
            "total_workload_cost_usd": strong_total_cost
        },
        "cost_savings_percentage": cost_savings_pct,
        "recommended_policy": "Use Fast Tier (8B) for 80% routing/scheduling tasks and Strong Tier (70B) for 20% complex triage."
    }


def get_llm_service() -> BaseLLMService:
    api_key = os.getenv("GROQ_API_KEY")
    # Verify api_key is configured and is not the default placeholder
    if api_key and api_key.strip() and api_key != "your_groq_api_key_here":
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return GroqLLMService(api_key=api_key, model=model)
    else:
        return MockLLMService()
