"""
app/services/security.py

Server-side Tool Authorization Engine and Role/Tool Permission Matrix.
Enforces:
1. Explicit Role-to-Tool permissions (Patient vs. Admin vs. Future roles).
2. Identity binding (Caller can only act on their own patient profile; Zero cross-patient access).
3. Patient Consent Framework (Active, unexpired consent required for protected health data tools).
4. Tool parameter validation and sanitization (Schema types, bounds, enum checks).
5. Minimum-necessary data limits (Clamping excessive batch queries).
6. Comprehensive audit metadata generation.

The LLM is NEVER the authority for authorization, consent, or access control.
"""

from typing import Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app import models
import logging

logger = logging.getLogger("caregraph.security")

# Permitted roles
ALLOWED_ROLES = {"patient", "admin"}

# Allowed Vital types
ALLOWED_VITAL_TYPES = {"blood_pressure", "heart_rate", "weight", "temperature", "spo2"}

# Maximum query limits to satisfy minimum-necessary data principles
MAX_RECORDS_LIMIT = 50
DEFAULT_RECORDS_LIMIT = 10

# Explicit Role/Tool Permission Matrix
# Mapping: tool_name -> Set of allowed roles
ROLE_TOOL_PERMISSIONS: Dict[str, Set[str]] = {
    # Patient self-service tools
    "get_patient_profile": {"patient"},
    "get_patient_medications": {"patient"},
    "get_patient_vitals": {"patient"},
    "store_vital": {"patient"},
    "calculate_vital_trend": {"patient"},
    "get_medication_schedule": {"patient"},
    "create_medication_reminder": {"patient"},
    "cancel_reminder": {"patient"},
    "book_appointment_slot": {"patient"},
    "cancel_appointment": {"patient"},
    
    # Shared / Public tools
    "search_available_slots": {"patient", "admin"},
    "get_grounded_knowledge": {"patient", "admin"},
    "general_conversation": {"patient", "admin"},
    "triage_symptom_assessment": {"patient", "admin"},
    
    # Admin-only tools (Cannot access clinical patient data directly)
    "manage_knowledge_docs": {"admin"},
    "inspect_audit_logs": {"admin"},
    "list_all_patients_demographics": {"admin"},
}

# Explicit mapping of tools to required patient consent type (None if unrestricted)
TOOL_CONSENT_REQUIREMENTS: Dict[str, Optional[str]] = {
    "get_patient_profile": "data_access",
    "get_patient_medications": "medication_tracking",
    "get_patient_vitals": "vital_tracking",
    "store_vital": "vital_tracking",
    "calculate_vital_trend": "vital_tracking",
    "get_medication_schedule": "medication_reminders",
    "create_medication_reminder": "medication_reminders",
    "cancel_reminder": "medication_reminders",
    "book_appointment_slot": "appointment_booking",
    "cancel_appointment": "appointment_booking",
    # Shared / Public tools (no consent required)
    "search_available_slots": None,
    "get_grounded_knowledge": None,
    "general_conversation": None,
    "triage_symptom_assessment": None,
    # Admin tools
    "manage_knowledge_docs": None,
    "inspect_audit_logs": None,
    "list_all_patients_demographics": None,
}


def check_patient_consent(
    db: Session,
    patient_id: int,
    consent_type: str
) -> Tuple[bool, Optional[str]]:
    """
    Verifies whether a patient has an active, unexpired, and granted consent for consent_type.
    If a patient is newly created with no consent records yet, initializes standard initial onboarding defaults.
    """
    from app import crud
    all_consents = crud.get_patient_consents(db, patient_id=patient_id)
    if not all_consents:
        # Initialize default standard consents
        now = datetime.now(timezone.utc)
        for c_type in [
            "data_access",
            "vital_tracking",
            "medication_tracking",
            "medication_reminders",
            "appointment_booking",
            "ai_processing",
        ]:
            db.add(models.PatientConsent(
                patient_id=patient_id,
                consent_type=c_type,
                status="granted",
                granted_at=now,
                expires_at=now + timedelta(days=365),
                version="v1.0"
            ))
        db.commit()

    consent = crud.get_patient_consent_by_type(db, patient_id=patient_id, consent_type=consent_type)
    if not consent:
        return False, f"Patient consent '{consent_type}' is missing. Please grant consent to access this health service."
    
    if consent.status == "revoked":
        return False, f"Patient consent '{consent_type}' has been revoked. Action blocked."

    if consent.status == "expired":
        return False, f"Patient consent '{consent_type}' has expired."

    if consent.status != "granted":
        return False, f"Patient consent '{consent_type}' is not active (status: {consent.status})."

    # Check date expiration
    if consent.expires_at is not None:
        now = datetime.now(timezone.utc)
        exp = consent.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            return False, f"Patient consent '{consent_type}' expired on {exp.strftime('%Y-%m-%d')}."

    return True, None


@dataclass
class ToolAuthResult:
    is_authorized: bool
    denial_reason: Optional[str] = None
    sanitized_params: Dict[str, Any] = field(default_factory=dict)
    audit_metadata: Dict[str, Any] = field(default_factory=dict)


class ToolAuthorizationEngine:
    """
    Centralized server-side authority for validating and authorizing tool execution.
    Executes BEFORE any tool code or DB mutation runs.
    """

    @classmethod
    def authorize_tool_call(
        cls,
        db: Session,
        user_id: int,
        role: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        target_patient_id: Optional[int] = None,
    ) -> ToolAuthResult:
        """
        Validates whether the authenticated user (user_id, role) is authorized
        to execute `tool_name` with `params`.
        """
        params = params or {}
        audit_metadata: Dict[str, Any] = {
            "actor_user_id": user_id,
            "actor_role": role,
            "tool_name": tool_name,
            "target_patient_id": target_patient_id,
            "minimum_necessary_applied": False,
        }

        # 1. Role validation
        if role not in ALLOWED_ROLES:
            audit_metadata["auth_outcome"] = "DENIED"
            audit_metadata["denial_reason"] = "UNKNOWN_OR_UNAUTHORIZED_ROLE"
            logger.warning(f"Tool Auth Denied: Invalid role '{role}' for user_id={user_id}")
            return ToolAuthResult(
                is_authorized=False,
                denial_reason="Role is not recognized by authorization engine.",
                audit_metadata=audit_metadata,
            )

        # 2. Check Role-Tool Permission Matrix
        permitted_roles = ROLE_TOOL_PERMISSIONS.get(tool_name)
        if permitted_roles is None:
            audit_metadata["auth_outcome"] = "DENIED"
            audit_metadata["denial_reason"] = "UNKNOWN_TOOL"
            logger.warning(f"Tool Auth Denied: Unregistered tool '{tool_name}'")
            return ToolAuthResult(
                is_authorized=False,
                denial_reason=f"Tool '{tool_name}' is not registered in permission matrix.",
                audit_metadata=audit_metadata,
            )

        if role not in permitted_roles:
            audit_metadata["auth_outcome"] = "DENIED"
            audit_metadata["denial_reason"] = f"ROLE_{role.upper()}_FORBIDDEN_FOR_TOOL"
            logger.warning(f"Tool Auth Denied: Role '{role}' cannot invoke '{tool_name}'")
            return ToolAuthResult(
                is_authorized=False,
                denial_reason=f"Role '{role}' is not permitted to execute '{tool_name}'.",
                audit_metadata=audit_metadata,
            )

        # 3. Patient identity binding & Cross-Patient Access Prevention (IDOR defense)
        actual_patient_id = None
        if role == "patient":
            patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
            if not patient:
                # If patient profile not yet created, create minimal demographic record
                patient = models.Patient(
                    user_id=user_id,
                    first_name=f"User_{user_id}",
                    last_name="Patient"
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)
                now = datetime.now(timezone.utc)
                for c_type in ["data_access", "vital_tracking", "medication_tracking", "medication_reminders", "appointment_booking", "ai_processing"]:
                    db.add(models.PatientConsent(
                        patient_id=patient.id,
                        consent_type=c_type,
                        status="granted",
                        granted_at=now,
                        expires_at=now + timedelta(days=365),
                        version="v1.0"
                    ))
                db.commit()
                db.refresh(patient)

            actual_patient_id = patient.id
            audit_metadata["patient_id"] = actual_patient_id

            # If a target_patient_id or patient_id param was passed, verify it matches caller's own ID
            supplied_pid = target_patient_id or params.get("patient_id")
            if supplied_pid is not None and int(supplied_pid) != actual_patient_id:
                audit_metadata["auth_outcome"] = "DENIED"
                audit_metadata["denial_reason"] = "CROSS_PATIENT_ACCESS_DENIED"
                logger.warning(
                    f"Cross-patient violation attempt: user_id={user_id} (patient_id={actual_patient_id}) "
                    f"attempted to access target_patient_id={supplied_pid}"
                )
                return ToolAuthResult(
                    is_authorized=False,
                    denial_reason="Unauthorized: Access to other patient records is prohibited.",
                    audit_metadata=audit_metadata,
                )

        # 4. Parameter validation and Minimum-Necessary data enforcement
        sanitized, err = cls._validate_and_sanitize_params(tool_name, params)
        if err:
            audit_metadata["auth_outcome"] = "DENIED"
            audit_metadata["denial_reason"] = f"INVALID_PARAMS: {err}"
            logger.warning(f"Tool Auth Denied for '{tool_name}': {err}")
            return ToolAuthResult(
                is_authorized=False,
                denial_reason=f"Parameter validation failed: {err}",
                audit_metadata=audit_metadata,
            )

        if sanitized.get("limit_clamped"):
            audit_metadata["minimum_necessary_applied"] = True
            sanitized.pop("limit_clamped", None)

        # 5. Consent Enforcement Gate (Milestone 2)
        required_consent = TOOL_CONSENT_REQUIREMENTS.get(tool_name)
        if required_consent and role == "patient" and actual_patient_id is not None:
            has_consent, consent_denial = check_patient_consent(
                db=db,
                patient_id=actual_patient_id,
                consent_type=required_consent
            )
            if not has_consent:
                audit_metadata["auth_outcome"] = "DENIED"
                audit_metadata["denial_reason"] = f"CONSENT_DENIED: {consent_denial}"
                logger.warning(
                    f"Consent Denied: user_id={user_id} patient_id={actual_patient_id} "
                    f"for tool '{tool_name}' (requires '{required_consent}'): {consent_denial}"
                )
                return ToolAuthResult(
                    is_authorized=False,
                    denial_reason=consent_denial,
                    audit_metadata=audit_metadata,
                )

        audit_metadata["auth_outcome"] = "GRANTED"
        return ToolAuthResult(
            is_authorized=True,
            sanitized_params=sanitized,
            audit_metadata=audit_metadata,
        )

    @classmethod
    def _validate_and_sanitize_params(
        cls, tool_name: str, params: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Enforces strict parameter types, enum validation, string lengths, and minimum-necessary bounds.
        """
        sanitized = dict(params)

        # Minimum-necessary limit sanitization
        if "limit" in sanitized:
            try:
                limit_val = int(sanitized["limit"])
                if limit_val <= 0:
                    return {}, "Parameter 'limit' must be a positive integer."
                if limit_val > MAX_RECORDS_LIMIT:
                    sanitized["limit"] = MAX_RECORDS_LIMIT
                    sanitized["limit_clamped"] = True
                else:
                    sanitized["limit"] = limit_val
            except (ValueError, TypeError):
                return {}, "Parameter 'limit' must be an integer."

        # Vital-specific validation
        if tool_name in ("get_patient_vitals", "calculate_vital_trend", "store_vital"):
            vital_type = sanitized.get("vital_type")
            if vital_type is not None:
                if vital_type not in ALLOWED_VITAL_TYPES:
                    return {}, f"Invalid vital_type '{vital_type}'. Allowed types: {sorted(ALLOWED_VITAL_TYPES)}"

        if tool_name == "store_vital":
            if not sanitized.get("vital_type"):
                return {}, "Parameter 'vital_type' is required."
            if not sanitized.get("value") or not str(sanitized.get("value")).strip():
                return {}, "Parameter 'value' is required and cannot be empty."
            # Max length for notes
            notes = sanitized.get("notes")
            if notes and len(str(notes)) > 500:
                sanitized["notes"] = str(notes)[:500]

        # Reminder-specific validation
        if tool_name == "create_medication_reminder":
            rem_text = sanitized.get("reminder_text")
            rem_time = sanitized.get("reminder_time")
            if not rem_text or not str(rem_text).strip():
                return {}, "Parameter 'reminder_text' cannot be empty."
            if len(str(rem_text)) > 200:
                sanitized["reminder_text"] = str(rem_text)[:200]
            if not rem_time or not str(rem_time).strip():
                return {}, "Parameter 'reminder_time' cannot be empty."

        if tool_name == "cancel_reminder":
            if "reminder_id" not in sanitized:
                return {}, "Parameter 'reminder_id' is required."
            try:
                sanitized["reminder_id"] = int(sanitized["reminder_id"])
            except (ValueError, TypeError):
                return {}, "Parameter 'reminder_id' must be an integer."

        # Scheduling validation
        if tool_name == "book_appointment_slot":
            if not sanitized.get("doctor_name"):
                return {}, "Parameter 'doctor_name' is required."
            if not sanitized.get("specialty"):
                return {}, "Parameter 'specialty' is required."
            if not sanitized.get("appointment_time"):
                return {}, "Parameter 'appointment_time' is required."

        if tool_name == "cancel_appointment":
            if "appointment_id" not in sanitized:
                return {}, "Parameter 'appointment_id' is required."
            try:
                sanitized["appointment_id"] = int(sanitized["appointment_id"])
            except (ValueError, TypeError):
                return {}, "Parameter 'appointment_id' must be an integer."

        return sanitized, None


def authorize_tool(
    db: Session,
    user_id: int,
    role: str,
    tool_name: str,
    params: Optional[Dict[str, Any]] = None,
    target_patient_id: Optional[int] = None,
) -> ToolAuthResult:
    """Convenience helper function for ToolAuthorizationEngine."""
    return ToolAuthorizationEngine.authorize_tool_call(
        db=db,
        user_id=user_id,
        role=role,
        tool_name=tool_name,
        params=params,
        target_patient_id=target_patient_id,
    )
