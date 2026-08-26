import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

def test_auth_and_access_flow():
    # 1. Register a new user
    username = "test_patient_user"
    password = "test_password"
    reg_response = client.post(
        "/auth/register",
        json={"username": username, "password": password, "role": "patient"}
    )
    # If the user already exists (from a previous test run), status could be 400.
    # Otherwise, it should be 201.
    assert reg_response.status_code in [201, 400]
    
    # 2. Login with correct credentials to get a token
    login_response = client.post(
        "/auth/login",
        data={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Access profile (fails because profile is not created yet)
    profile_response = client.get("/patients/me", headers=headers)
    assert profile_response.status_code == 404
    
    # 4. Create patient profile
    create_profile_response = client.post(
        "/patients/me",
        json={
            "first_name": "Test",
            "last_name": "User",
            "date_of_birth": "1990-01-01",
            "gender": "Female",
            "email": "test@example.com",
            "phone": "+1-555-9999"
        },
        headers=headers
    )
    assert create_profile_response.status_code == 201
    
    # 5. Access profile now (should succeed)
    profile_response = client.get("/patients/me", headers=headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["first_name"] == "Test"
    assert profile_data["last_name"] == "User"
    assert profile_data["email"] == "test@example.com"
    
    # 6. Try accessing admin endpoint (should fail for patient role)
    admin_response = client.get("/admin/patients", headers=headers)
    assert admin_response.status_code == 403
    
    # 7. Login as admin and access admin endpoint (should succeed)
    admin_login = client.post(
        "/auth/login",
        data={"username": "admin_demo", "password": "admin_pass"}
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    admin_response = client.get("/admin/patients", headers=admin_headers)
    assert admin_response.status_code == 200
    patients_list = admin_response.json()
    assert len(patients_list) >= 1

def test_login_invalid_credentials():
    login_response = client.post(
        "/auth/login",
        data={"username": "non_existent_user", "password": "wrong_password"}
    )
    assert login_response.status_code == 401

def test_mock_llm_service():
    from app.services.llm import MockLLMService
    from app.schemas_ai import IntentEnum
    
    service = MockLLMService()
    assert service.is_mock_mode() is True
    
    # Test emergency intent
    intent_info = service.extract_intent("Help, this is an emergency!")
    assert intent_info.intent == IntentEnum.EMERGENCY
    assert intent_info.confidence == 1.0
    
    # Test triage intent
    intent_info = service.extract_intent("I have a bad cough and fever")
    assert intent_info.intent == IntentEnum.TRIAGE
    assert "cough" in intent_info.extracted_entities["symptom"]
    
    # Test scheduling intent
    intent_info = service.extract_intent("I want to book an appointment tomorrow")
    assert intent_info.intent == IntentEnum.SCHEDULING

def test_chat_patient_mock_mode():
    # 1. Register and login a patient
    username = "chat_test_patient"
    password = "chat_test_password"
    
    client.post(
        "/auth/register",
        json={"username": username, "password": password, "role": "patient"}
    )
    
    login_response = client.post(
        "/auth/login",
        data={"username": username, "password": password}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Query chat endpoint
    response = client.post(
        "/chat",
        json={"message": "I want to schedule a visit with doctor tomorrow"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "scheduling"
    assert data["is_mock"] is True
    assert data["approval_required"] is True
    assert "confirm" in data["message"].lower()


def test_chat_unauthenticated_role():
    # Unauthenticated request
    response = client.post(
        "/chat",
        json={"message": "Hello"}
    )
    assert response.status_code == 401

    # Unauthorized role request (Admin role is blocked)
    login_response = client.post(
        "/auth/login",
        data={"username": "admin_demo", "password": "admin_pass"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        "/chat",
        json={"message": "Hello"},
        headers=headers
    )
    assert response.status_code == 403

def test_chat_invalid_payload():
    # Register and login patient
    login_response = client.post(
        "/auth/login",
        data={"username": "chat_test_patient", "password": "chat_test_password"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Empty JSON body
    response = client.post(
        "/chat",
        json={},
        headers=headers
    )
    assert response.status_code == 422  # Validation error

def test_chat_error_mappings(monkeypatch):
    import app.services.llm
    from app.services.llm import (
        LLMAuthenticationError,
        LLMTimeoutError,
        LLMConnectionError,
        LLMRateLimitError
    )
    
    # Login patient
    login_response = client.post(
        "/auth/login",
        data={"username": "chat_test_patient", "password": "chat_test_password"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Mock LLM service instance to raise custom errors
    class ErrorLLMService(app.services.llm.BaseLLMService):
        def __init__(self, exc_to_raise):
            self.exc_to_raise = exc_to_raise
        def extract_intent(self, text):
            raise self.exc_to_raise
        def generate_response(self, text, intent_info):
            raise self.exc_to_raise
        def is_mock_mode(self):
            return True

    # 1. Timeout -> 504 Gateway Timeout
    monkeypatch.setattr(app.services.llm, "get_llm_service", lambda: ErrorLLMService(LLMTimeoutError()))
    res = client.post("/chat", json={"message": "test"}, headers=headers)
    assert res.status_code == 504
    assert "timed out" in res.json()["detail"].lower()
    
    # 2. Authentication -> 503 Service Unavailable
    monkeypatch.setattr(app.services.llm, "get_llm_service", lambda: ErrorLLMService(LLMAuthenticationError()))
    res = client.post("/chat", json={"message": "test"}, headers=headers)
    assert res.status_code == 503
    assert "unable to authenticate" in res.json()["detail"].lower()
    
    # 3. Connection -> 503 Service Unavailable
    monkeypatch.setattr(app.services.llm, "get_llm_service", lambda: ErrorLLMService(LLMConnectionError()))
    res = client.post("/chat", json={"message": "test"}, headers=headers)
    assert res.status_code == 503
    assert "check network connectivity" in res.json()["detail"].lower()
    
    # 4. Rate Limit -> 429 Too Many Requests
    monkeypatch.setattr(app.services.llm, "get_llm_service", lambda: ErrorLLMService(LLMRateLimitError()))
    res = client.post("/chat", json={"message": "test"}, headers=headers)
    assert res.status_code == 429
    assert "busy" in res.json()["detail"].lower()
    
    # 5. Generic Error -> 503 Service Unavailable (without exposing raw detail)
    monkeypatch.setattr(app.services.llm, "get_llm_service", lambda: ErrorLLMService(Exception("Some raw internal details")))
    res = client.post("/chat", json={"message": "test"}, headers=headers)
    assert res.status_code == 503
    assert "encountered an error processing" in res.json()["detail"].lower()
    assert "some raw internal details" not in res.json()["detail"].lower()


def test_chat_scheduling_hitl_endpoint_flow():
    # 1. Register & Login Patient A
    username = "hitl_patient_a"
    password = "hitl_password_a"
    client.post("/auth/register", json={"username": username, "password": password, "role": "patient"})
    login_res = client.post("/auth/login", data={"username": username, "password": password})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    session_id = "sess_sched_100"

    # 2. Send scheduling chat query -> Returns approval_required = True
    chat_res = client.post(
        "/chat",
        json={"message": "I want to schedule an appointment with dermatologist tomorrow", "session_id": session_id},
        headers=headers
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data["intent"] == "scheduling"
    assert data["approval_required"] is True
    assert data["approval_status"] == "pending"
    assert "confirm" in data["message"].lower()

    # 3. Test Invalid Approval decision -> 400 Bad Request
    bad_approve_res = client.post(
        "/chat/approve",
        json={"session_id": session_id, "decision": "maybe"},
        headers=headers
    )
    assert bad_approve_res.status_code == 400

    # 4. Test Cross-Patient Security: Patient B cannot approve Patient A's thread -> 404 Not Found
    username_b = "hitl_patient_b"
    password_b = "hitl_password_b"
    client.post("/auth/register", json={"username": username_b, "password": password_b, "role": "patient"})
    login_b = client.post("/auth/login", data={"username": username_b, "password": password_b})
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    cross_res = client.post(
        "/chat/approve",
        json={"session_id": session_id, "decision": "approved"},
        headers=headers_b
    )
    assert cross_res.status_code == 404

    # 5. Patient A approves scheduling request -> 200 OK with approval confirmation
    approve_res = client.post(
        "/chat/approve",
        json={"session_id": session_id, "decision": "approved"},
        headers=headers
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["approval_required"] is False
    assert approved_data["approval_status"] == "approved"
    assert "confirmed" in approved_data["message"].lower()
    assert "appointment id" in approved_data["message"].lower()


def test_chat_approve_rejection_flow():
    # Login patient
    login_res = client.post("/auth/login", data={"username": "hitl_patient_a", "password": "hitl_password_a"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
    session_id = "sess_sched_200"

    # Send scheduling request
    client.post("/chat", json={"message": "Book appointment for doctor next week", "session_id": session_id}, headers=headers)

    # Reject request
    reject_res = client.post(
        "/chat/approve",
        json={"session_id": session_id, "decision": "rejected"},
        headers=headers
    )
    assert reject_res.status_code == 200
    rejected_data = reject_res.json()
    assert rejected_data["approval_required"] is False
    assert rejected_data["approval_status"] == "rejected"
    assert "rejected by user" in rejected_data["message"].lower()


def test_chat_approve_not_found():
    login_res = client.post("/auth/login", data={"username": "hitl_patient_a", "password": "hitl_password_a"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
    
    res = client.post(
        "/chat/approve",
        json={"session_id": "non_existent_session_999", "decision": "approved"},
        headers=headers
    )
    assert res.status_code == 404


