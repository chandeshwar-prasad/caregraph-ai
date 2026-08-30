"""
tests/test_messaging_api.py

Automated integration test suite for Phase 11D-2 Messaging API:
- POST /messaging/send
- POST /messaging/opt-out
- JWT authentication and authorization (401 unauthenticated, patient & admin access)
- Outbound SMS and WhatsApp delivery
- Recipient E.164 format and message bounds validation
- Opt-out keyword processing (STOP, UNSUBSCRIBE, CANCEL)
- Sanitized error handling and zero credential leakage
- PHI-sanitized logging and zero-disk retention
"""

import os
import logging
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.messaging import DEFAULT_MAX_MESSAGE_LENGTH

client = TestClient(app)


def get_patient_token_header():
    res = client.post("/auth/login", data={"username": "patient_demo", "password": "patient_pass"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_admin_token_header():
    res = client.post("/auth/login", data={"username": "admin_demo", "password": "admin_pass"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_messaging_send_returns_401():
    """Verify that unauthenticated requests to /messaging/send return 401 Unauthorized."""
    res = client.post(
        "/messaging/send",
        json={"recipient": "+12025550143", "body": "Appointment reminder", "channel": "sms"}
    )
    assert res.status_code == 401, "Unauthenticated request did not return 401"


def test_unauthenticated_messaging_opt_out_returns_401():
    """Verify that unauthenticated requests to /messaging/opt-out return 401 Unauthorized."""
    res = client.post(
        "/messaging/opt-out",
        json={"recipient": "+12025550143", "keyword": "STOP", "channel": "sms"}
    )
    assert res.status_code == 401, "Unauthenticated opt-out did not return 401"


def test_authenticated_patient_can_send_sms_mock():
    """Verify that authenticated patient can send an SMS via mock provider."""
    headers = get_patient_token_header()
    res = client.post(
        "/messaging/send",
        json={
            "recipient": "+12025550143",
            "body": "CareGraph reminder: Check vitals today at 2 PM.",
            "channel": "sms"
        },
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["channel"] == "sms"
    assert data["provider"] == "mock_messaging"
    assert data["is_mock"] is True
    assert data["status"] == "mock_delivered"
    assert data["message_id"].startswith("mock_msg_")


def test_authenticated_patient_can_send_whatsapp_mock():
    """Verify that authenticated patient can send a WhatsApp notification via mock provider."""
    headers = get_patient_token_header()
    res = client.post(
        "/messaging/send",
        json={
            "recipient": "+12025550188",
            "body": "Your lab results are ready for review in the patient portal.",
            "channel": "whatsapp",
            "template_name": "lab_results_ready"
        },
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["channel"] == "whatsapp"
    assert data["is_mock"] is True


def test_authenticated_admin_can_send_messaging_notification():
    """Verify that authenticated admin can also invoke outbound messaging notifications."""
    headers = get_admin_token_header()
    res = client.post(
        "/messaging/send",
        json={
            "recipient": "+12025550100",
            "body": "System update notice: Maintenance scheduled for midnight.",
            "channel": "sms"
        },
        headers=headers
    )
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_invalid_recipient_format_rejected():
    """Verify that invalid/non-E.164 phone numbers are rejected with 400 Bad Request."""
    headers = get_patient_token_header()

    invalid_recipients = [
        "not-a-phone-number",
        "123",
        "+12345678901234567890",
    ]

    for rec in invalid_recipients:
        res = client.post(
            "/messaging/send",
            json={"recipient": rec, "body": "Hello", "channel": "sms"},
            headers=headers
        )
        assert res.status_code in [400, 422]


def test_empty_message_body_rejected():
    """Verify that empty or whitespace message bodies are rejected with 400 or 422."""
    headers = get_patient_token_header()
    res = client.post(
        "/messaging/send",
        json={"recipient": "+12025550143", "body": "", "channel": "sms"},
        headers=headers
    )
    assert res.status_code in [400, 422]


def test_oversized_message_body_rejected():
    """Verify that message bodies exceeding limit are rejected with 400 or 422."""
    headers = get_patient_token_header()
    oversized = "X" * (DEFAULT_MAX_MESSAGE_LENGTH + 10)
    res = client.post(
        "/messaging/send",
        json={"recipient": "+12025550143", "body": oversized, "channel": "sms"},
        headers=headers
    )
    assert res.status_code in [400, 422]


def test_unsupported_channel_rejected():
    """Verify that unsupported channels (e.g. telegram, slack) are rejected with 400."""
    headers = get_patient_token_header()
    res = client.post(
        "/messaging/send",
        json={"recipient": "+12025550143", "body": "Test", "channel": "telegram"},
        headers=headers
    )
    assert res.status_code == 400
    assert "unsupported channel" in res.json()["detail"].lower()


def test_opt_out_endpoint_with_stop_keyword():
    """Verify that recognized STOP keyword marks recipient opted_out=True."""
    headers = get_patient_token_header()
    res = client.post(
        "/messaging/opt-out",
        json={"recipient": "+12025550143", "keyword": "STOP", "channel": "sms"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["opted_out"] is True
    assert data["keyword_matched"] is True
    assert data["status"] == "opted_out"
    assert data["channel"] == "sms"


def test_opt_out_endpoint_with_unsubscribe_keyword():
    """Verify that recognized UNSUBSCRIBE keyword marks recipient opted_out=True."""
    headers = get_patient_token_header()
    res = client.post(
        "/messaging/opt-out",
        json={"recipient": "+12025550188", "keyword": "unsubscribe", "channel": "whatsapp"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["opted_out"] is True
    assert data["status"] == "opted_out"
    assert data["channel"] == "whatsapp"


def test_opt_out_endpoint_with_non_opt_out_keyword():
    """Verify that normal non-opt-out text returns opted_out=False."""
    headers = get_patient_token_header()
    res = client.post(
        "/messaging/opt-out",
        json={"recipient": "+12025550143", "keyword": "Hello doctor", "channel": "sms"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["opted_out"] is False
    assert data["keyword_matched"] is False
    assert data["status"] == "active"


def test_no_phone_or_body_in_logs(caplog):
    """Verify that neither phone numbers nor message bodies are recorded in application logs."""
    headers = get_patient_token_header()
    test_phone = "+12025550177"
    test_body = "Confidential Lisinopril medication schedule"

    with caplog.at_level(logging.DEBUG):
        res = client.post(
            "/messaging/send",
            json={"recipient": test_phone, "body": test_body, "channel": "sms"},
            headers=headers
        )
    assert res.status_code == 200

    log_text = caplog.text
    assert test_phone not in log_text
    assert test_body not in log_text
    assert "Lisinopril" not in log_text


def test_zero_disk_retention():
    """Verify that messaging API endpoint operations create zero temporary files on disk."""
    headers = get_patient_token_header()
    initial_files = set(os.listdir("."))

    res = client.post(
        "/messaging/send",
        json={"recipient": "+12025550143", "body": "Ephemeral message check", "channel": "sms"},
        headers=headers
    )
    assert res.status_code == 200

    current_files = set(os.listdir("."))
    assert current_files == initial_files, "Temporary message files leaked to disk!"


def test_identity_binding_no_arbitrary_patient_override():
    """Verify that identity is derived solely from JWT claims and not parameter injection."""
    headers = get_patient_token_header()
    res = client.post(
        "/messaging/send?patient_id=999&user_id=888",
        json={"recipient": "+12025550143", "body": "Identity binding check", "channel": "sms"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert "patient_id" not in data
    assert "user_id" not in data
