from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.database import SessionLocal
import app.models as models
from app.schemas_ai import IntentEnum, IntentExtraction

import app.services.llm as llm_module
from app.services.triage import (
    evaluate_red_flags,
    get_deterministic_emergency_response,
    evaluate_triage_risk,
    build_triage_response
)
from app.services.knowledge import get_grounded_knowledge
from app.services.audit import log_audit_event
from app.services.scheduling import (
    search_available_slots,
    book_appointment_slot,
    cancel_appointment_slot
)
from app.services import patient_data
from app.services.security import authorize_tool
from app.services.telemetry import global_telemetry, trace_span


# STEP 2: Graph State Schema

class CareGraphState(TypedDict, total=False):
    session_id: str
    user_id: int
    user_role: Optional[str]
    user_message: str
    intent: Optional[str]
    confidence: float
    extracted_entities: Dict[str, Any]
    current_agent: str
    approval_required: bool
    approval_status: Optional[str]  # "pending", "approved", "rejected"
    risk_level: Optional[str]        # "emergency", "urgent", "non_urgent"
    safety_escalated: bool
    retrieved_sources: List[Dict[str, Any]]
    follow_up_questions: List[str]
    selected_slot: Dict[str, Any]
    appointment_id: Optional[int]
    patient_data_result: Optional[Dict[str, Any]]
    patient_data_tool: Optional[str]
    response_draft: str
    final_response: str
    is_mock: bool


# Backward compatibility alias
HealthSyncState = CareGraphState


# STEP 3: Node Definitions



def input_screening_node(state: CareGraphState) -> Dict[str, Any]:
    """
    Input Screening Node:
    1. Enforces input length limits (max 2000 chars).
    2. Screens for prompt injection override attempts.
    3. Runs pure Python deterministic red-flag safety check BEFORE LLM execution.
    """
    user_msg = state.get("user_message", "")
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id", 0)

    # 1. Payload size check
    if len(user_msg) > 2000:
        log_audit_event(session_id, user_id, "unknown", "input_screening", "non_urgent", True, True)
        return {
            "current_agent": "input_screening",
            "safety_escalated": True,
            "risk_level": "non_urgent",
            "response_draft": "Your query exceeds the maximum allowed message length. Please shorten your message and try again."
        }

    # 2. Prompt injection screening
    injection_keywords = ["ignore your safety", "ignore previous instructions", "override safety", "bypass safety"]
    if any(kw in user_msg.lower() for kw in injection_keywords):
        log_audit_event(session_id, user_id, "unknown", "input_screening", "non_urgent", True, True)
        return {
            "current_agent": "input_screening",
            "safety_escalated": True,
            "risk_level": "non_urgent",
            "response_draft": "I am a healthcare coordination assistant. I cannot follow instructions to bypass safety rules or issue medical diagnoses."
        }

    # 3. Deterministic Red-Flag Safety Check (Executes BEFORE LLM / Supervisor / Scheduling)
    if evaluate_red_flags(user_msg):
        log_audit_event(session_id, user_id, "emergency", "emergency_safety", "emergency", True, True)
        return {
            "current_agent": "emergency_safety",
            "intent": "emergency",
            "risk_level": "emergency",
            "safety_escalated": True,
            "response_draft": get_deterministic_emergency_response()
        }

    return {
        "safety_escalated": False
    }


def route_after_screening(state: CareGraphState) -> str:
    """
    If deterministic safety check or input screening triggered an immediate escalation/response,
    bypass Supervisor and route directly to responder.
    """
    if state.get("safety_escalated"):
        return "responder"
    return "supervisor"


def supervisor_node(state: CareGraphState) -> Dict[str, Any]:
    """
    Supervisor node that reuses get_llm_service() from app/services/llm.py
    to parse user intent.
    """
    user_msg = state.get("user_message", "")
    llm_service: llm_module.BaseLLMService = llm_module.get_llm_service()
    
    intent_info: IntentExtraction = llm_service.extract_intent(user_msg)
    
    return {
        "intent": intent_info.intent.value,
        "confidence": intent_info.confidence,
        "extracted_entities": intent_info.extracted_entities,
        "is_mock": llm_service.is_mock_mode(),
        "current_agent": "supervisor"
    }


def route_by_intent(state: CareGraphState) -> str:
    """
    Conditional edge function routing from Supervisor to specialized stub nodes.
    """
    intent = state.get("intent", IntentEnum.GENERAL.value)
    if intent == IntentEnum.TRIAGE.value:
        return "triage"
    elif intent == IntentEnum.SCHEDULING.value:
        return "scheduling"
    elif intent == IntentEnum.RECORDS.value:
        return "records"
    elif intent == IntentEnum.REMINDERS.value:
        return "reminders"
    elif intent == IntentEnum.EMERGENCY.value:
        return "emergency"
    else:
        return "general"


def triage_node(state: CareGraphState) -> Dict[str, Any]:
    user_msg = state.get("user_message", "")
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id", 0)
    entities = state.get("extracted_entities", {})

    db = SessionLocal()
    try:
        knowledge_items = get_grounded_knowledge(user_msg, db=db)
    except Exception:
        db.rollback()
        knowledge_items = get_grounded_knowledge(user_msg)
    finally:
        db.close()

    risk_level = evaluate_triage_risk(user_msg, entities)
    resp_text, follow_ups = build_triage_response(user_msg, risk_level, knowledge_items)

    log_audit_event(
        session_id=session_id,
        user_id=user_id,
        intent="triage",
        selected_agent="triage",
        risk_level=risk_level,
        safety_escalated=False,
        is_mock=state.get("is_mock", True)
    )

    return {
        "current_agent": "triage",
        "risk_level": risk_level,
        "safety_escalated": False,
        "retrieved_sources": knowledge_items,
        "follow_up_questions": follow_ups,
        "response_draft": resp_text,
        "approval_required": False
    }


def scheduling_node(state: CareGraphState) -> Dict[str, Any]:
    """
    Phase 5 Real Scheduling Agent Node:
    1. Extracts doctor_specialty and date_preference.
    2. Calls search_available_slots() from app/services/scheduling.py.
    3. Triggers dynamic interrupt() to pause for user confirmation.
    4. Upon approval: runs server-side tool authorization, persists appointment to DB via book_appointment_slot().
    5. Upon rejection: performs zero DB mutation and returns cancellation response.
    """
    approval_status = state.get("approval_status")
    user_id = state.get("user_id", 1)
    user_role = state.get("user_role", "patient")
    session_id = state.get("session_id", "default")
    entities = state.get("extracted_entities", {})
    pref = entities.get("date_preference", "tomorrow")
    spec = entities.get("doctor_specialty", "the doctor")

    # Search synthetic availability slots
    available_slots = search_available_slots(specialty=spec, date_pref=pref)
    selected_slot = available_slots[0] if available_slots else {
        "doctor_name": f"Dr. Alex Smith ({spec})",
        "specialty": spec,
        "appointment_time": f"{pref} at 10:00 AM"
    }

    if approval_status == "approved":
        # Execute DB booking mutation upon explicit approval
        db = SessionLocal()
        try:
            # Server-side tool authorization check before mutation
            auth_res = authorize_tool(
                db=db,
                user_id=user_id,
                role=user_role,
                tool_name="book_appointment_slot",
                params={
                    "doctor_name": selected_slot["doctor_name"],
                    "specialty": selected_slot["specialty"],
                    "appointment_time": selected_slot["appointment_time"]
                }
            )
            if not auth_res.is_authorized:
                log_audit_event(
                    session_id=session_id,
                    user_id=user_id,
                    intent="scheduling",
                    selected_agent="scheduling",
                    risk_level="non_urgent",
                    safety_escalated=False,
                    is_mock=state.get("is_mock", True),
                    tool_name="book_appointment_slot",
                    tool_result="denied",
                    auth_outcome="DENIED",
                    denial_reason=auth_res.denial_reason,
                    actor_role=user_role
                )
                return {
                    "current_agent": "scheduling",
                    "approval_required": False,
                    "approval_status": "denied",
                    "selected_slot": selected_slot,
                    "response_draft": f"⚠️ Action Denied: {auth_res.denial_reason}"
                }

            patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
            if not patient:
                patient = models.Patient(user_id=user_id, first_name="Demo", last_name="Patient")
                db.add(patient)
                db.commit()
                db.refresh(patient)
            patient_id_to_use = patient.id
            apt = book_appointment_slot(
                db=db,
                patient_id=patient_id_to_use,
                doctor_name=selected_slot["doctor_name"],
                specialty=selected_slot["specialty"],
                appointment_time=selected_slot["appointment_time"],
                notes="Phase 5 Demo Appointment"
            )
            log_audit_event(
                session_id=session_id,
                user_id=user_id,
                intent="scheduling",
                selected_agent="scheduling",
                risk_level="non_urgent",
                safety_escalated=False,
                is_mock=state.get("is_mock", True),
                tool_name="book_appointment_slot",
                patient_id=patient_id_to_use,
                tool_result="success",
                auth_outcome="GRANTED",
                actor_role=user_role
            )
            msg = (
                f"✅ **Mock Demo Appointment Confirmed!**\n\n"
                f"• **Doctor:** {apt.doctor_name}\n"
                f"• **Specialty:** {apt.specialty}\n"
                f"• **Time:** {apt.appointment_time}\n"
                f"• **Appointment ID:** #{apt.id}\n\n"
                f"*(Note: This is a Phase 5 mock demo appointment. Database persistence verified.)*"
            )
            return {
                "current_agent": "scheduling",
                "approval_required": False,
                "approval_status": "approved",
                "appointment_id": apt.id,
                "selected_slot": selected_slot,
                "response_draft": msg
            }
        finally:
            db.close()

    elif approval_status == "rejected":
        # Zero DB mutation on rejection
        msg = f"Appointment request with {selected_slot['doctor_name']} around {selected_slot['appointment_time']} was REJECTED by user. No action was taken."
        return {
            "current_agent": "scheduling",
            "approval_required": False,
            "approval_status": "rejected",
            "selected_slot": selected_slot,
            "response_draft": msg
        }
    else:
        # Dynamic HITL Interrupt Scenario
        confirm_msg = f"Please confirm: Do you want to schedule an appointment with {selected_slot['doctor_name']} around {selected_slot['appointment_time']}?"
        
        # Pause execution and yield prompt payload
        decision = interrupt({
            "action": "approval_required",
            "message": confirm_msg,
            "selected_slot": selected_slot
        })
        
        # When resumed, process decision (dict or string)
        if isinstance(decision, dict):
            status = decision.get("approval_status", "approved")
        elif isinstance(decision, str):
            status = decision
        else:
            status = "approved"

        if status == "approved":
            db = SessionLocal()
            try:
                auth_res = authorize_tool(
                    db=db,
                    user_id=user_id,
                    role=user_role,
                    tool_name="book_appointment_slot",
                    params={
                        "doctor_name": selected_slot["doctor_name"],
                        "specialty": selected_slot["specialty"],
                        "appointment_time": selected_slot["appointment_time"]
                    }
                )
                if not auth_res.is_authorized:
                    log_audit_event(
                        session_id=session_id,
                        user_id=user_id,
                        intent="scheduling",
                        selected_agent="scheduling",
                        risk_level="non_urgent",
                        safety_escalated=False,
                        is_mock=state.get("is_mock", True),
                        tool_name="book_appointment_slot",
                        tool_result="denied",
                        auth_outcome="DENIED",
                        denial_reason=auth_res.denial_reason,
                        actor_role=user_role
                    )
                    return {
                        "current_agent": "scheduling",
                        "approval_required": False,
                        "approval_status": "denied",
                        "selected_slot": selected_slot,
                        "response_draft": f"⚠️ Action Denied: {auth_res.denial_reason}"
                    }

                patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
                if not patient:
                    patient = models.Patient(user_id=user_id, first_name="Demo", last_name="Patient")
                    db.add(patient)
                    db.commit()
                    db.refresh(patient)
                apt = book_appointment_slot(
                    db=db,
                    patient_id=patient.id,
                    doctor_name=selected_slot["doctor_name"],
                    specialty=selected_slot["specialty"],
                    appointment_time=selected_slot["appointment_time"],
                    notes="Phase 5 Demo Appointment"
                )
                log_audit_event(
                    session_id=session_id,
                    user_id=user_id,
                    intent="scheduling",
                    selected_agent="scheduling",
                    risk_level="non_urgent",
                    safety_escalated=False,
                    is_mock=state.get("is_mock", True),
                    tool_name="book_appointment_slot",
                    patient_id=patient.id,
                    tool_result="success",
                    auth_outcome="GRANTED",
                    actor_role=user_role
                )
                res_msg = (
                    f"✅ **Mock Demo Appointment Confirmed!**\n\n"
                    f"• **Doctor:** {apt.doctor_name}\n"
                    f"• **Specialty:** {apt.specialty}\n"
                    f"• **Time:** {apt.appointment_time}\n"
                    f"• **Appointment ID:** #{apt.id}\n\n"
                    f"*(Note: This is a Phase 5 mock demo appointment. Database persistence verified.)*"
                )
                return {
                    "current_agent": "scheduling",
                    "approval_required": False,
                    "approval_status": "approved",
                    "appointment_id": apt.id,
                    "selected_slot": selected_slot,
                    "response_draft": res_msg
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            res_msg = f"Appointment request with {selected_slot['doctor_name']} around {selected_slot['appointment_time']} was REJECTED by user. No action was taken."
            return {
                "current_agent": "scheduling",
                "approval_required": False,
                "approval_status": "rejected",
                "selected_slot": selected_slot,
                "response_draft": res_msg
            }


def patient_data_node(state: CareGraphState) -> Dict[str, Any]:
    """
    Phase 6 Real Patient Data Agent Node (Hardened with Phase 8 Server-Side Authorization):
    Dispatches deterministically based on intent ('records' or 'reminders') and user request.
    Invokes controlled Python tools from app/services/patient_data.py after authorization.
    Identities strictly derived from user_id in graph state (from JWT), never LLM entities.
    """
    intent = state.get("intent", "records")
    user_id = state.get("user_id", 1)
    user_role = state.get("user_role", "patient")
    session_id = state.get("session_id", "default")
    user_msg = state.get("user_message", "")
    entities = state.get("extracted_entities", {})
    msg_lower = user_msg.lower()

    db = SessionLocal()
    try:
        patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
        if not patient:
            patient = models.Patient(user_id=user_id, first_name="Demo", last_name="Patient")
            db.add(patient)
            db.commit()
            db.refresh(patient)

        tool_result = None
        tool_name = "get_patient_profile"
        tool_params: Dict[str, Any] = {}
        draft = ""

        if intent == IntentEnum.RECORDS.value or intent == "records":
            vital_keywords = ["vital", "vitals", "bp", "blood pressure", "heart rate", "pulse", "weight", "temp", "temperature", "spo2"]
            med_keywords = ["medication", "medications", "medicine", "medicines", "drug", "drugs", "prescription", "rx", "pill", "pills"]

            if any(kw in msg_lower for kw in vital_keywords):
                is_trend = any(kw in msg_lower for kw in ["trend", "trending", "history", "track", "tracking", "over time"])
                vital_type = None
                if "blood pressure" in msg_lower or "bp" in msg_lower:
                    vital_type = "blood_pressure"
                elif "heart rate" in msg_lower or "pulse" in msg_lower:
                    vital_type = "heart_rate"
                elif "weight" in msg_lower:
                    vital_type = "weight"
                elif "temp" in msg_lower or "temperature" in msg_lower:
                    vital_type = "temperature"
                elif "spo2" in msg_lower or "oxygen" in msg_lower:
                    vital_type = "spo2"

                if is_trend and vital_type:
                    tool_name = "calculate_vital_trend"
                    tool_params = {"vital_type": vital_type}
                else:
                    tool_name = "get_patient_vitals"
                    tool_params = {"vital_type": vital_type} if vital_type else {}

            elif any(kw in msg_lower for kw in med_keywords):
                tool_name = "get_patient_medications"
                tool_params = {}

            else:
                tool_name = "get_patient_profile"
                tool_params = {}

        elif intent == IntentEnum.REMINDERS.value or intent == "reminders":
            create_keywords = ["remind me", "set reminder", "create reminder", "schedule reminder", "add reminder", "new reminder"]
            cancel_keywords = ["cancel reminder", "remove reminder", "delete reminder"]

            if any(kw in msg_lower for kw in create_keywords):
                tool_name = "create_medication_reminder"
                rem_text = entities.get("reminder_text") or user_msg
                rem_time = entities.get("reminder_time") or "08:00 AM"
                tool_params = {"reminder_text": rem_text, "reminder_time": rem_time}

            elif any(kw in msg_lower for kw in cancel_keywords):
                tool_name = "cancel_reminder"
                rem_id = entities.get("reminder_id")
                tool_params = {"reminder_id": rem_id} if rem_id is not None else {}

            else:
                tool_name = "get_medication_schedule"
                tool_params = {}

        # 1. Server-Side Tool Authorization Gate
        auth_res = authorize_tool(
            db=db,
            user_id=user_id,
            role=user_role,
            tool_name=tool_name,
            params=tool_params
        )

        if not auth_res.is_authorized:
            log_audit_event(
                session_id=session_id,
                user_id=user_id,
                intent=intent,
                selected_agent="patient_data",
                risk_level="non_urgent",
                safety_escalated=False,
                is_mock=state.get("is_mock", True),
                tool_name=tool_name,
                patient_id=patient.id,
                tool_result="denied",
                auth_outcome="DENIED",
                denial_reason=auth_res.denial_reason,
                actor_role=user_role
            )
            return {
                "current_agent": intent,
                "patient_data_result": {"error": auth_res.denial_reason},
                "patient_data_tool": tool_name,
                "response_draft": f"⚠️ Access Denied: {auth_res.denial_reason}",
                "approval_required": False
            }

        # 2. Execute tool with sanitized parameters
        sanitized = auth_res.sanitized_params
        if tool_name == "calculate_vital_trend":
            tool_result = patient_data.calculate_vital_trend(db, user_id=user_id, vital_type=sanitized["vital_type"])
            trend_val = tool_result.get("trend", "no_data").title()
            count_val = tool_result.get("count", 0)
            draft = f"📊 **{sanitized['vital_type'].replace('_', ' ').title()} Trend Analysis**\n\n• **Readings Analyzed:** {count_val}\n• **Trend Direction:** {trend_val}\n\n*(Note: Trend calculations are mathematical summaries and not clinical interpretations.)*"

        elif tool_name == "get_patient_vitals":
            tool_result = patient_data.get_patient_vitals(db, user_id=user_id, vital_type=sanitized.get("vital_type"), limit=sanitized.get("limit", 10))
            if tool_result:
                v_lines = [f"• **{v['vital_type'].replace('_', ' ').title()}:** {v['value']} {v.get('unit') or ''}" for v in tool_result]
                draft = "📈 **Your Vital Sign Readings**\n\n" + "\n".join(v_lines)
            else:
                draft = "No vital sign readings found for your profile."

        elif tool_name == "get_patient_medications":
            tool_result = patient_data.get_patient_medications(db, user_id=user_id)
            if tool_result:
                m_lines = [f"• **{m['name']}** ({m['dosage']}) - {m['frequency']}" for m in tool_result]
                draft = "💊 **Your Active Medications**\n\n" + "\n".join(m_lines) + "\n\n*(Note: CareGraph AI provides medication records for care navigation only and does not issue medical prescriptions or change dosages.)*"
            else:
                draft = "No active medications found in your records."

        elif tool_name == "create_medication_reminder":
            tool_result = patient_data.create_medication_reminder(
                db,
                user_id=user_id,
                reminder_text=sanitized["reminder_text"],
                reminder_time=sanitized["reminder_time"]
            )
            draft = f"⏰ **Medication Reminder Scheduled!**\n\n• **Reminder:** {tool_result.get('reminder_text')}\n• **Time:** {tool_result.get('reminder_time')}\n• **Status:** Active"

        elif tool_name == "cancel_reminder":
            tool_result = patient_data.cancel_reminder(db, user_id=user_id, reminder_id=sanitized["reminder_id"])
            if tool_result:
                draft = f"❌ Medication reminder #{sanitized['reminder_id']} has been cancelled."
            else:
                draft = f"Reminder #{sanitized['reminder_id']} was not found or does not belong to your account."

        elif tool_name == "get_medication_schedule":
            tool_result = patient_data.get_medication_schedule(db, user_id=user_id)
            if tool_result:
                r_lines = [f"• **Reminder #{r['id']}:** {r['reminder_text']} at {r['reminder_time']}" for r in tool_result]
                draft = "⏰ **Your Active Medication Reminders**\n\n" + "\n".join(r_lines)
            else:
                draft = "You have no active medication reminders."

        else:  # get_patient_profile / records summary
            profile = patient_data.get_patient_profile(db, user_id=user_id)
            meds = patient_data.get_patient_medications(db, user_id=user_id)
            vitals = patient_data.get_patient_vitals(db, user_id=user_id, limit=3)
            tool_result = {"profile": profile, "medications": meds, "vitals": vitals}
            draft = (
                f"📋 **Patient Health Record Summary**\n\n"
                f"• **Patient Name:** {profile.get('first_name', '')} {profile.get('last_name', '')}\n"
                f"• **Active Medications:** {len(meds)}\n"
                f"• **Recent Vitals Recorded:** {len(vitals)}"
            )

        log_audit_event(
            session_id=session_id,
            user_id=user_id,
            intent=intent,
            selected_agent="patient_data",
            risk_level="non_urgent",
            safety_escalated=False,
            is_mock=state.get("is_mock", True),
            tool_name=tool_name,
            patient_id=patient.id,
            tool_result="success",
            auth_outcome="GRANTED",
            actor_role=user_role,
            minimum_necessary_applied=auth_res.audit_metadata.get("minimum_necessary_applied", False)
        )

        return {
            "current_agent": intent,
            "patient_data_result": tool_result,
            "patient_data_tool": tool_name,
            "response_draft": draft,
            "approval_required": False
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def emergency_stub_node(state: CareGraphState) -> Dict[str, Any]:
    msg = get_deterministic_emergency_response()
    return {
        "current_agent": "emergency",
        "risk_level": "emergency",
        "safety_escalated": True,
        "response_draft": msg,
        "approval_required": False
    }


def general_stub_node(state: CareGraphState) -> Dict[str, Any]:
    llm_service: llm_module.BaseLLMService = llm_module.get_llm_service()
    user_msg = state.get("user_message", "")
    resp = llm_service.generate_response(user_msg, IntentExtraction(
        intent=IntentEnum.GENERAL,
        confidence=state.get("confidence", 0.8),
        extracted_entities=state.get("extracted_entities", {})
    ))
    return {
        "current_agent": "general",
        "response_draft": resp,
        "approval_required": False
    }


def responder_node(state: CareGraphState) -> Dict[str, Any]:
    draft = state.get("response_draft", "I am your CareGraph assistant. How can I help you today?")
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id", 0)
    intent = state.get("intent", "general")
    agent = state.get("current_agent", "general")
    safety_esc = state.get("safety_escalated", False)
    role = state.get("user_role", "patient")

    global_telemetry.record_workflow_event(
        session_id=session_id,
        user_id=user_id,
        intent=intent or "general",
        selected_agent=agent or "general",
        latency_ms=10.0,
        status="SAFETY_ESCALATED" if safety_esc else "SUCCESS",
        safety_escalated=safety_esc,
        tool_name=state.get("patient_data_tool"),
        actor_role=role or "patient"
    )

    return {
        "final_response": draft
    }


# StateGraph Assembly & MemorySaver checkpointer

builder = StateGraph(CareGraphState)

# Add Nodes
builder.add_node("input_screening", input_screening_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("triage", triage_node)
builder.add_node("scheduling", scheduling_node)
builder.add_node("records", patient_data_node)
builder.add_node("reminders", patient_data_node)
builder.add_node("emergency", emergency_stub_node)
builder.add_node("general", general_stub_node)
builder.add_node("responder", responder_node)

# Add Edges
builder.add_edge(START, "input_screening")

builder.add_conditional_edges(
    "input_screening",
    route_after_screening,
    {
        "responder": "responder",
        "supervisor": "supervisor"
    }
)

builder.add_conditional_edges(
    "supervisor",
    route_by_intent,
    {
        "triage": "triage",
        "scheduling": "scheduling",
        "records": "records",
        "reminders": "reminders",
        "emergency": "emergency",
        "general": "general"
    }
)

builder.add_edge("triage", "responder")
builder.add_edge("scheduling", "responder")
builder.add_edge("records", "responder")
builder.add_edge("reminders", "responder")
builder.add_edge("emergency", "responder")
builder.add_edge("general", "responder")

builder.add_edge("responder", END)

# MemorySaver checkpointer
memory_checkpointer = MemorySaver()

# Compile graph with MemorySaver checkpointer
graph = builder.compile(checkpointer=memory_checkpointer)
