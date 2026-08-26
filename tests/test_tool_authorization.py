"""
tests/test_tool_authorization.py

Comprehensive tests for Phase 8 Milestone 1:
Server-side Tool Authorization Engine, Role/Tool Permission Matrix,
Parameter Validation, Minimum-Necessary Rule, and Audit Hardening.
"""

import pytest
from app.database import SessionLocal
from app import models, crud
from app.auth import hash_password
from app.services.security import (
    ToolAuthorizationEngine,
    authorize_tool,
    ROLE_TOOL_PERMISSIONS,
    MAX_RECORDS_LIMIT,
    ALLOWED_VITAL_TYPES,
)
from app.services.audit import log_audit_event
from app.services.graph import graph


@pytest.fixture(scope="module")
def setup_auth_test_users():
    """Create test patient user and admin user for authorization tests."""
    db = SessionLocal()
    try:
        # Create Patient 1
        p1_user = db.query(models.User).filter(models.User.username == "auth_patient_1").first()
        if not p1_user:
            p1_user = models.User(
                username="auth_patient_1",
                password_hash=hash_password("pass123"),
                role="patient"
            )
            db.add(p1_user)
            db.commit()
            db.refresh(p1_user)
            p1_profile = models.Patient(
                user_id=p1_user.id,
                first_name="Alice",
                last_name="Smith",
                email="alice@example.com"
            )
            db.add(p1_profile)
            db.commit()
            db.refresh(p1_profile)
        else:
            p1_profile = p1_user.patient

        # Create Patient 2
        p2_user = db.query(models.User).filter(models.User.username == "auth_patient_2").first()
        if not p2_user:
            p2_user = models.User(
                username="auth_patient_2",
                password_hash=hash_password("pass123"),
                role="patient"
            )
            db.add(p2_user)
            db.commit()
            db.refresh(p2_user)
            p2_profile = models.Patient(
                user_id=p2_user.id,
                first_name="Bob",
                last_name="Jones",
                email="bob@example.com"
            )
            db.add(p2_profile)
            db.commit()
            db.refresh(p2_profile)
        else:
            p2_profile = p2_user.patient

        # Create Admin
        admin_user = db.query(models.User).filter(models.User.username == "auth_admin_user").first()
        if not admin_user:
            admin_user = models.User(
                username="auth_admin_user",
                password_hash=hash_password("adminpass"),
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        return {
            "p1_user_id": p1_user.id,
            "p1_patient_id": p1_profile.id,
            "p2_user_id": p2_user.id,
            "p2_patient_id": p2_profile.id,
            "admin_user_id": admin_user.id,
        }
    finally:
        db.close()


def test_permission_matrix_patient_allowed_tools(setup_auth_test_users):
    """Verify that patient role is authorized for patient self-service tools."""
    db = SessionLocal()
    try:
        user_id = setup_auth_test_users["p1_user_id"]
        
        patient_tools = [
            "get_patient_profile",
            "get_patient_medications",
            "get_patient_vitals",
            "calculate_vital_trend",
            "get_medication_schedule",
        ]
        
        for tool in patient_tools:
            res = authorize_tool(db, user_id=user_id, role="patient", tool_name=tool)
            assert res.is_authorized is True, f"Expected {tool} to be authorized for patient"
            assert res.audit_metadata.get("auth_outcome") == "GRANTED"
    finally:
        db.close()


def test_permission_matrix_patient_denied_admin_tools(setup_auth_test_users):
    """Verify that patient role is denied admin management tools."""
    db = SessionLocal()
    try:
        user_id = setup_auth_test_users["p1_user_id"]
        admin_tools = ["manage_knowledge_docs", "inspect_audit_logs", "list_all_patients_demographics"]
        
        for tool in admin_tools:
            res = authorize_tool(db, user_id=user_id, role="patient", tool_name=tool)
            assert res.is_authorized is False, f"Expected {tool} to be DENIED for patient"
            assert "ROLE_PATIENT_FORBIDDEN_FOR_TOOL" in res.audit_metadata.get("denial_reason", "")
            assert res.audit_metadata.get("auth_outcome") == "DENIED"
    finally:
        db.close()


def test_permission_matrix_admin_denied_direct_patient_clinical_tools(setup_auth_test_users):
    """Verify that admin role is denied direct execution of patient personal clinical tools."""
    db = SessionLocal()
    try:
        admin_id = setup_auth_test_users["admin_user_id"]
        clinical_tools = [
            "get_patient_medications",
            "get_patient_vitals",
            "store_vital",
            "calculate_vital_trend",
            "get_medication_schedule",
            "create_medication_reminder",
            "book_appointment_slot",
        ]
        
        for tool in clinical_tools:
            res = authorize_tool(db, user_id=admin_id, role="admin", tool_name=tool)
            assert res.is_authorized is False, f"Expected {tool} to be DENIED for admin"
            assert "ROLE_ADMIN_FORBIDDEN_FOR_TOOL" in res.audit_metadata.get("denial_reason", "")
    finally:
        db.close()


def test_permission_matrix_shared_tools(setup_auth_test_users):
    """Verify shared tools are accessible to both patient and admin."""
    db = SessionLocal()
    try:
        p_id = setup_auth_test_users["p1_user_id"]
        a_id = setup_auth_test_users["admin_user_id"]
        
        shared_tools = ["search_available_slots", "get_grounded_knowledge", "general_conversation", "triage_symptom_assessment"]
        
        for tool in shared_tools:
            res_p = authorize_tool(db, user_id=p_id, role="patient", tool_name=tool)
            res_a = authorize_tool(db, user_id=a_id, role="admin", tool_name=tool)
            assert res_p.is_authorized is True
            assert res_a.is_authorized is True
    finally:
        db.close()


def test_unregistered_tool_and_invalid_role(setup_auth_test_users):
    """Verify unknown tools and invalid roles are rejected."""
    db = SessionLocal()
    try:
        p_id = setup_auth_test_users["p1_user_id"]
        
        # Unknown tool
        res = authorize_tool(db, user_id=p_id, role="patient", tool_name="arbitrary_unregistered_tool")
        assert res.is_authorized is False
        assert "UNKNOWN_TOOL" in res.audit_metadata.get("denial_reason", "")
        
        # Invalid role
        res_role = authorize_tool(db, user_id=p_id, role="hacker_role", tool_name="get_patient_profile")
        assert res_role.is_authorized is False
        assert "UNKNOWN_OR_UNAUTHORIZED_ROLE" in res_role.audit_metadata.get("denial_reason", "")
    finally:
        db.close()


def test_cross_patient_access_prevention(setup_auth_test_users):
    """Verify IDOR prevention: Patient 1 cannot execute tools targeting Patient 2."""
    db = SessionLocal()
    try:
        p1_user_id = setup_auth_test_users["p1_user_id"]
        p2_patient_id = setup_auth_test_users["p2_patient_id"]
        
        # Patient 1 explicitly supplies Patient 2's patient_id in target_patient_id
        res = authorize_tool(
            db=db,
            user_id=p1_user_id,
            role="patient",
            tool_name="get_patient_profile",
            target_patient_id=p2_patient_id
        )
        assert res.is_authorized is False
        assert res.audit_metadata.get("denial_reason") == "CROSS_PATIENT_ACCESS_DENIED"
        
        # Patient 1 explicitly supplies Patient 2's patient_id in params
        res2 = authorize_tool(
            db=db,
            user_id=p1_user_id,
            role="patient",
            tool_name="get_patient_vitals",
            params={"patient_id": p2_patient_id}
        )
        assert res2.is_authorized is False
        assert res2.audit_metadata.get("denial_reason") == "CROSS_PATIENT_ACCESS_DENIED"
    finally:
        db.close()


def test_parameter_validation_and_sanitization(setup_auth_test_users):
    """Verify tool parameter schema and range validations."""
    db = SessionLocal()
    try:
        p_id = setup_auth_test_users["p1_user_id"]
        
        # Invalid vital type
        res_vital = authorize_tool(
            db=db,
            user_id=p_id,
            role="patient",
            tool_name="get_patient_vitals",
            params={"vital_type": "invalid_vital_name"}
        )
        assert res_vital.is_authorized is False
        assert "Invalid vital_type" in res_vital.denial_reason

        # Valid vital type
        for vt in ALLOWED_VITAL_TYPES:
            res_v_ok = authorize_tool(
                db=db,
                user_id=p_id,
                role="patient",
                tool_name="get_patient_vitals",
                params={"vital_type": vt}
            )
            assert res_v_ok.is_authorized is True

        # Missing required parameter in store_vital
        res_missing = authorize_tool(
            db=db,
            user_id=p_id,
            role="patient",
            tool_name="store_vital",
            params={"vital_type": "heart_rate"}  # value missing
        )
        assert res_missing.is_authorized is False
        assert "Parameter 'value' is required" in res_missing.denial_reason

        # Invalid reminder_id type in cancel_reminder
        res_bad_rem = authorize_tool(
            db=db,
            user_id=p_id,
            role="patient",
            tool_name="cancel_reminder",
            params={"reminder_id": "not_an_integer"}
        )
        assert res_bad_rem.is_authorized is False
        assert "must be an integer" in res_bad_rem.denial_reason
    finally:
        db.close()


def test_minimum_necessary_data_clamping(setup_auth_test_users):
    """Verify minimum-necessary limit clamping on query tools."""
    db = SessionLocal()
    try:
        p_id = setup_auth_test_users["p1_user_id"]
        
        # Excessive limit requested
        res = authorize_tool(
            db=db,
            user_id=p_id,
            role="patient",
            tool_name="get_patient_vitals",
            params={"limit": 500}
        )
        assert res.is_authorized is True
        assert res.sanitized_params["limit"] == MAX_RECORDS_LIMIT
        assert res.audit_metadata.get("minimum_necessary_applied") is True

        # Negative limit requested
        res_neg = authorize_tool(
            db=db,
            user_id=p_id,
            role="patient",
            tool_name="get_patient_vitals",
            params={"limit": -5}
        )
        assert res_neg.is_authorized is False
        assert "positive integer" in res_neg.denial_reason
    finally:
        db.close()


def test_graph_patient_data_tool_authorization_denial(setup_auth_test_users):
    """Verify that graph node halts execution and returns clean rejection when role is unauthorized."""
    p_id = setup_auth_test_users["p1_user_id"]
    
    # Run graph with an unauthorized role attempting patient records
    config = {"configurable": {"thread_id": f"test_auth_graph_{p_id}"}}
    initial_state = {
        "user_message": "What medications am I currently taking?",
        "user_id": p_id,
        "user_role": "unknown_intruder_role",
        "session_id": f"test_auth_graph_{p_id}"
    }
    
    result = graph.invoke(initial_state, config=config)
    # Final response must indicate access denied and not execute tool
    assert "Access Denied" in result.get("final_response", "") or "Role is not recognized" in result.get("final_response", "")


def test_audit_logging_structure_and_zero_phi():
    """Verify that audit logger produces structured events without PHI."""
    event = log_audit_event(
        session_id="session_test_999",
        user_id=42,
        intent="records",
        selected_agent="patient_data",
        risk_level="non_urgent",
        safety_escalated=False,
        tool_name="get_patient_medications",
        patient_id=10,
        tool_result="success",
        auth_outcome="GRANTED",
        actor_role="patient",
        minimum_necessary_applied=True
    )
    
    assert event["user_id"] == 42
    assert event["auth_outcome"] == "GRANTED"
    assert event["actor_role"] == "patient"
    assert event["minimum_necessary_applied"] is True
    assert "timestamp" in event
    # Check that sensitive clinical message content is not present
    assert "user_message" not in event
    assert "password" not in event
    assert "notes" not in event
