"""
tests/test_messaging_service.py

Automated unit and integration test suite for Phase 11D-1 Messaging Service Layer:
- Outbound SMS and WhatsApp channels
- MockMessagingService offline and deterministic execution
- Rejection of unsupported channels, empty/oversized bodies, and malformed recipients
- Provider factory fallback and credential resolution
- Structured response schema compliance (MessagingSendResponse)
- Zero-disk retention & PHI-sanitized logging
- Opt-out keyword detection & consent integration hooks
- Exception safety without credential leakage
"""

import os
import logging
import pytest
from app.services.messaging import (
    BaseMessagingService,
    MockMessagingService,
    CloudMessagingService,
    MessagingServiceFactory,
    MessagingError,
    MessagingAuthenticationError,
    MessagingConnectionError,
    MessagingPayloadError,
    MessagingRecipientError,
    get_messaging_service,
    is_opt_out_keyword,
    DEFAULT_MAX_MESSAGE_LENGTH,
)
from app.schemas_ai import MessagingSendResponse


def test_mock_sms_send_succeeds():
    """Verify that MockMessagingService successfully sends an SMS."""
    service = MockMessagingService()
    assert service.is_mock_mode() is True

    result = service.send_message(
        recipient="+12025550143",
        body="Your appointment reminder for tomorrow at 10:00 AM.",
        channel="sms"
    )
    assert result["success"] is True
    assert result["channel"] == "sms"
    assert result["is_mock"] is True
    assert result["status"] == "mock_delivered"
    assert result["message_id"].startswith("mock_msg_")


def test_mock_whatsapp_send_succeeds():
    """Verify that MockMessagingService successfully sends a WhatsApp message."""
    service = MockMessagingService()
    result = service.send_message(
        recipient="+12025550188",
        body="CareGraph AI: Please confirm your upcoming visit.",
        channel="whatsapp"
    )
    assert result["success"] is True
    assert result["channel"] == "whatsapp"
    assert result["is_mock"] is True


def test_unsupported_channel_is_rejected():
    """Verify that unsupported channels (e.g. email, telegram, push) raise MessagingPayloadError."""
    service = MockMessagingService()
    with pytest.raises(MessagingPayloadError) as exc_info:
        service.send_message(
            recipient="+12025550143",
            body="Test message",
            channel="telegram"
        )
    assert "unsupported channel" in str(exc_info.value).lower()


def test_empty_message_is_rejected():
    """Verify that empty or whitespace-only message bodies raise MessagingPayloadError."""
    service = MockMessagingService()

    with pytest.raises(MessagingPayloadError) as exc_info:
        service.send_message(recipient="+12025550143", body="", channel="sms")
    assert "empty" in str(exc_info.value).lower()

    with pytest.raises(MessagingPayloadError) as exc_info:
        service.send_message(recipient="+12025550143", body="   ", channel="sms")
    assert "empty" in str(exc_info.value).lower()


def test_oversized_message_is_rejected():
    """Verify that message bodies exceeding DEFAULT_MAX_MESSAGE_LENGTH raise MessagingPayloadError."""
    service = MockMessagingService()
    oversized_body = "A" * (DEFAULT_MAX_MESSAGE_LENGTH + 10)

    with pytest.raises(MessagingPayloadError) as exc_info:
        service.send_message(recipient="+12025550143", body=oversized_body, channel="sms")
    assert "exceeds maximum allowed length" in str(exc_info.value).lower()


def test_invalid_recipient_is_rejected():
    """Verify that invalid, non-E.164, or alphabetic recipient values raise MessagingRecipientError."""
    service = MockMessagingService()

    invalid_recipients = [
        "",
        "invalid_phone",
        "123",  # Too short
        "+12345678901234567890",  # Too long (> 15 digits)
        "not-a-number@test.com",
    ]

    for rec in invalid_recipients:
        with pytest.raises(MessagingRecipientError):
            service.send_message(recipient=rec, body="Test message", channel="sms")


def test_missing_and_placeholder_credentials_fallback():
    """Verify that missing or placeholder credentials safely fall back to MockMessagingService."""
    # Placeholder SID/Token
    service = MessagingServiceFactory.get_messaging_service(
        account_sid="your_twilio_account_sid",
        auth_token="your_twilio_auth_token"
    )
    assert isinstance(service, MockMessagingService)
    assert service.is_mock_mode() is True

    # Empty SID raises MessagingAuthenticationError on direct instantiation
    with pytest.raises(MessagingAuthenticationError) as exc_info:
        CloudMessagingService(account_sid="", auth_token="secret", from_number="+1000")
    assert "invalid or missing account sid" in str(exc_info.value).lower()


def test_provider_exceptions_are_sanitized():
    """Verify that Cloud provider exceptions do not leak credentials or sensitive tokens."""
    cloud_service = CloudMessagingService(
        account_sid="AC_dummy_account_1234567890",
        auth_token="super_secret_token_abcdef123456",
        from_number="+12025550100"
    )

    # When attempting delivery to unreachable mock URL, connection error is raised without credential leakage
    with pytest.raises(MessagingConnectionError) as exc_info:
        cloud_service.send_message(recipient="+12025550143", body="Test message", channel="sms")

    err_str = str(exc_info.value)
    assert "super_secret_token" not in err_str
    assert "AC_dummy_account" not in err_str


def test_structured_result_schema_compliance():
    """Verify that messaging return payload strictly conforms to MessagingSendResponse schema."""
    service = MockMessagingService()
    result = service.send_message(
        recipient="+12025550143",
        body="Health check reminder",
        channel="sms"
    )

    response_model = MessagingSendResponse(**result)
    assert response_model.success is True
    assert response_model.channel == "sms"
    assert response_model.provider == "mock_messaging"
    assert response_model.is_mock is True
    assert response_model.status == "mock_delivered"


def test_no_message_body_or_recipient_in_logs(caplog):
    """Verify that application logs contain only sanitized metadata, never message text or phone numbers."""
    service = MockMessagingService()
    test_phone = "+12025550199"
    test_body = "Confidential clinical reminder Lisinopril 10mg"

    with caplog.at_level(logging.DEBUG):
        service.send_message(recipient=test_phone, body=test_body, channel="sms")

    log_text = caplog.text
    assert test_phone not in log_text
    assert test_body not in log_text
    assert "Confidential" not in log_text
    assert "Lisinopril" not in log_text


def test_zero_disk_retention():
    """Verify that messaging execution leaves zero temporary files on disk."""
    initial_files = set(os.listdir("."))
    service = MockMessagingService()

    service.send_message(recipient="+12025550143", body="Ephemeral notification", channel="sms")

    current_files = set(os.listdir("."))
    assert current_files == initial_files, "Temporary message files were leaked to disk!"


def test_mock_provider_performs_no_network_calls(monkeypatch):
    """Verify that MockMessagingService runs completely offline without network sockets."""
    # If any socket connection is attempted, fail the test
    import socket
    def raise_network_attempt(*args, **kwargs):
        raise RuntimeError("Network call attempted by Mock provider!")
    monkeypatch.setattr(socket, "socket", raise_network_attempt)

    service = MockMessagingService()
    result = service.send_message(recipient="+12025550143", body="Offline test", channel="sms")
    assert result["success"] is True


def test_opt_out_keyword_recognition():
    """Verify standard opt-out keywords (STOP, UNSUBSCRIBE, CANCEL) are recognized."""
    assert is_opt_out_keyword("STOP") is True
    assert is_opt_out_keyword("stop") is True
    assert is_opt_out_keyword(" unsubscribe ") is True
    assert is_opt_out_keyword("CANCEL") is True
    assert is_opt_out_keyword("QUIT") is True
    assert is_opt_out_keyword("Hello doctor") is False
    assert is_opt_out_keyword("") is False


def test_global_factory_helper():
    """Verify get_messaging_service convenience helper returns BaseMessagingService."""
    service = get_messaging_service(channel="whatsapp")
    assert isinstance(service, BaseMessagingService)
    assert service.is_mock_mode() is True
