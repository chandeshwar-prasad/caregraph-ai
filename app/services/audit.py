import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Configure audit logger
logger = logging.getLogger("caregraph.audit")
logger.setLevel(logging.INFO)


def log_audit_event(
    session_id: str,
    user_id: int,
    intent: str,
    selected_agent: str,
    risk_level: str,
    safety_escalated: bool,
    is_mock: bool = True,
    tool_name: Optional[str] = None,
    patient_id: Optional[int] = None,
    tool_result: Optional[str] = None,
    auth_outcome: Optional[str] = None,
    denial_reason: Optional[str] = None,
    actor_role: Optional[str] = None,
    minimum_necessary_applied: Optional[bool] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Logs structured workflow and security authorization execution event metadata.
    Strictly avoids storing sensitive clinical free text, passwords, or PHI.
    """
    audit_record: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "user_id": user_id,
        "intent": intent,
        "selected_agent": selected_agent,
        "risk_level": risk_level,
        "safety_escalated": safety_escalated,
        "is_mock": is_mock
    }
    if actor_role is not None:
        audit_record["actor_role"] = actor_role
    if tool_name is not None:
        audit_record["tool_name"] = tool_name
    if patient_id is not None:
        audit_record["patient_id"] = patient_id
    if auth_outcome is not None:
        audit_record["auth_outcome"] = auth_outcome
    if denial_reason is not None:
        audit_record["denial_reason"] = denial_reason
    if minimum_necessary_applied is not None:
        audit_record["minimum_necessary_applied"] = minimum_necessary_applied
    if tool_result is not None:
        audit_record["tool_result"] = tool_result
    if extra_metadata:
        for k, v in extra_metadata.items():
            if k not in audit_record and not any(p in k.lower() for p in ["message", "password", "notes", "text"]):
                audit_record[k] = v

    logger.info(f"AUDIT_EVENT: {audit_record}")
    return audit_record
