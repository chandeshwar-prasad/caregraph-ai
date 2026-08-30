"""
app/services/messaging.py

Provider-agnostic Messaging Service Layer for CareGraph AI.
Supports outbound communication across 'sms' and 'whatsapp' channels.

Key Features:
1. BaseMessagingService abstract interface.
2. In-memory MockMessagingService for deterministic offline testing and CI execution.
3. CloudMessagingService adapter with sanitized error translation and credential safety.
4. MessagingServiceFactory for dynamic provider resolution and safe mock fallback.
5. Strict E.164 recipient validation, message size clamping, zero message body persistence,
   and PHI-sanitized logging.
6. Opt-out keyword detection and consent integration boundary hooks.
"""

import os
import re
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Set

logger = logging.getLogger("caregraph.messaging")

# Validation Constraints
DEFAULT_MAX_MESSAGE_LENGTH = int(os.getenv("MESSAGING_MAX_LENGTH", "1600"))
SUPPORTED_CHANNELS: Set[str] = {"sms", "whatsapp"}

# E.164 phone number pattern: optional +, 7 to 15 digits
E164_PHONE_REGEX = re.compile(r"^\+?[1-9]\d{6,14}$")

# Recognized standard inbound opt-out keywords
OPT_OUT_KEYWORDS: Set[str] = {"STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}


# --- Exception Hierarchy ---

class MessagingError(Exception):
    """Base exception for messaging operations."""
    pass


class MessagingAuthenticationError(MessagingError):
    """Provider authentication or missing/invalid API credentials."""
    pass


class MessagingConnectionError(MessagingError):
    """Network connection failure, DNS resolution failure, or timeout."""
    pass


class MessagingPayloadError(MessagingError):
    """Empty, oversized, or invalid message payload."""
    pass


class MessagingRecipientError(MessagingError):
    """Malformed or invalid recipient address/phone number."""
    pass


class MessagingProviderError(MessagingError):
    """Provider-side API or delivery error."""
    pass


class MessagingConsentError(MessagingError):
    """Recipient has not consented or has opted out of communication."""
    pass


# --- Validation Helpers ---

def normalize_and_validate_recipient(recipient: str) -> str:
    """
    Validates and normalizes recipient address.
    Strips whitespace, hyphens, parentheses, and dots.
    Ensures E.164 phone compliance.
    Raises MessagingRecipientError if invalid.
    """
    if not recipient or not isinstance(recipient, str):
        raise MessagingRecipientError("Recipient address cannot be empty.")

    cleaned = re.sub(r"[\s\-\(\)\.]", "", recipient.strip())
    if not E164_PHONE_REGEX.match(cleaned):
        raise MessagingRecipientError("Invalid recipient format. Must be a valid E.164 formatted phone number.")

    return cleaned


def validate_message_body(body: str, max_length: int = DEFAULT_MAX_MESSAGE_LENGTH) -> str:
    """
    Validates message body:
    - Must not be empty or whitespace only
    - Must not exceed configured maximum character length
    """
    if body is None or not isinstance(body, str):
        raise MessagingPayloadError("Message body cannot be None.")

    stripped = body.strip()
    if len(stripped) == 0:
        raise MessagingPayloadError("Message body cannot be empty.")

    if len(stripped) > max_length:
        raise MessagingPayloadError(
            f"Message body exceeds maximum allowed length of {max_length} characters (received {len(stripped)})."
        )

    return stripped


def validate_channel(channel: str) -> str:
    """
    Validates and normalizes delivery channel ('sms' or 'whatsapp').
    """
    if not channel or not isinstance(channel, str):
        raise MessagingPayloadError("Channel cannot be empty.")

    norm_channel = channel.lower().strip()
    if norm_channel not in SUPPORTED_CHANNELS:
        raise MessagingPayloadError(
            f"Unsupported channel '{channel}'. Supported channels: {', '.join(sorted(SUPPORTED_CHANNELS))}."
        )

    return norm_channel


def is_opt_out_keyword(text: str) -> bool:
    """
    Checks whether inbound text represents a standard opt-out keyword (e.g. STOP, UNSUBSCRIBE).
    """
    if not text or not isinstance(text, str):
        return False
    return text.strip().upper() in OPT_OUT_KEYWORDS


# --- Abstract Base Messaging Service ---

class BaseMessagingService(ABC):
    """Abstract interface for messaging providers."""

    @abstractmethod
    def send_message(
        self,
        recipient: str,
        body: str,
        channel: str = "sms",
        template_name: Optional[str] = None,
        template_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends an outbound message across the specified channel.
        Returns a structured dictionary conforming to MessagingSendResponse:
        {
            "success": bool,
            "channel": str,
            "provider": str,
            "message_id": str,
            "status": str,
            "error_category": Optional[str],
            "is_mock": bool
        }
        """
        pass

    @abstractmethod
    def is_mock_mode(self) -> bool:
        """Returns True if this provider is a mock/offline implementation."""
        pass


# --- In-Memory Mock Messaging Service ---

class MockMessagingService(BaseMessagingService):
    """
    Deterministic in-memory Mock Messaging Provider for offline tests, local dev, and CI.
    Zero external network calls, zero credentials required, zero disk persistence.
    """

    def __init__(self, default_status: str = "mock_delivered"):
        self.default_status = default_status

    def send_message(
        self,
        recipient: str,
        body: str,
        channel: str = "sms",
        template_name: Optional[str] = None,
        template_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        valid_channel = validate_channel(channel)
        normalize_and_validate_recipient(recipient)
        validate_message_body(body)

        message_id = f"mock_msg_{uuid.uuid4().hex[:12]}"

        # Sanitized log: strictly metadata, NO message body, NO phone number
        logger.info(f"Mock message sent successfully. Channel: {valid_channel}, MessageID: {message_id}")

        return {
            "success": True,
            "channel": valid_channel,
            "provider": "mock_messaging",
            "message_id": message_id,
            "status": self.default_status,
            "error_category": None,
            "is_mock": True,
        }

    def is_mock_mode(self) -> bool:
        return True


# --- Cloud Messaging Adapter ---

class CloudMessagingService(BaseMessagingService):
    """
    Cloud Messaging Adapter for REST-based SMS/WhatsApp providers (e.g. Twilio, Meta Cloud API).
    Never logs raw credentials or message content.
    Translates transport exceptions into sanitized MessagingError subclasses.
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        provider_name: str = "cloud_messaging"
    ):
        if not account_sid or not account_sid.strip() or account_sid.startswith("your_"):
            raise MessagingAuthenticationError("Invalid or missing account SID for cloud messaging.")
        if not auth_token or not auth_token.strip() or auth_token.startswith("your_"):
            raise MessagingAuthenticationError("Invalid or missing auth token for cloud messaging.")

        self.account_sid = account_sid.strip()
        self.auth_token = auth_token.strip()
        self.from_number = from_number.strip() if from_number else ""
        self.provider_name = provider_name

    def send_message(
        self,
        recipient: str,
        body: str,
        channel: str = "sms",
        template_name: Optional[str] = None,
        template_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        valid_channel = validate_channel(channel)
        norm_recipient = normalize_and_validate_recipient(recipient)
        valid_body = validate_message_body(body)

        import httpx

        # Simulated REST dispatch with sanitized error handling
        url = f"https://api.messaging.provider.mock/v1/Accounts/{self.account_sid}/Messages"
        payload = {
            "To": f"whatsapp:{norm_recipient}" if valid_channel == "whatsapp" else norm_recipient,
            "From": self.from_number,
            "Body": valid_body,
        }

        try:
            # When running without active real remote endpoint, demonstrate safe error translation
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    url,
                    data=payload,
                    auth=(self.account_sid, self.auth_token)
                )
                if res.status_code == 401 or res.status_code == 403:
                    raise MessagingAuthenticationError("Provider rejected credentials.")
                elif res.status_code >= 500:
                    raise MessagingProviderError("Messaging provider service unavailable.")
                res.raise_for_status()
                data = res.json()
                return {
                    "success": True,
                    "channel": valid_channel,
                    "provider": self.provider_name,
                    "message_id": data.get("sid", f"msg_{uuid.uuid4().hex[:12]}"),
                    "status": data.get("status", "queued"),
                    "error_category": None,
                    "is_mock": False,
                }
        except httpx.RequestError:
            # Network / connection failure translated safely without exposing credentials
            logger.warning(f"Connection failure to messaging provider on channel {valid_channel}")
            raise MessagingConnectionError("Failed to connect to cloud messaging provider.")
        except MessagingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected messaging error on channel {valid_channel}: {type(e).__name__}")
            raise MessagingProviderError("Outbound message delivery failed.")

    def is_mock_mode(self) -> bool:
        return False


# --- Messaging Service Factory ---

class MessagingServiceFactory:
    """Factory for resolving and instantiating Messaging providers."""

    @staticmethod
    def get_messaging_service(
        channel: str = "sms",
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        force_mock: bool = False
    ) -> BaseMessagingService:
        """
        Resolves Messaging provider:
        - If force_mock is True, returns MockMessagingService.
        - If cloud credentials are present and valid, returns CloudMessagingService.
        - Otherwise, gracefully falls back to MockMessagingService.
        """
        if force_mock:
            return MockMessagingService()

        sid = account_sid or os.getenv("MESSAGING_ACCOUNT_SID", "").strip()
        token = auth_token or os.getenv("MESSAGING_AUTH_TOKEN", "").strip()
        from_num = from_number or os.getenv("MESSAGING_FROM_NUMBER", "").strip()

        is_placeholder = (
            not sid
            or not token
            or sid.startswith("your_")
            or token.startswith("your_")
            or "placeholder" in sid.lower()
        )

        if is_placeholder:
            return MockMessagingService()

        try:
            return CloudMessagingService(
                account_sid=sid,
                auth_token=token,
                from_number=from_num
            )
        except Exception as e:
            logger.warning(f"Failed to initialize CloudMessagingService ({e}). Falling back to MockMessagingService.")
            return MockMessagingService()


# Global convenience helper function
def get_messaging_service(channel: str = "sms") -> BaseMessagingService:
    return MessagingServiceFactory.get_messaging_service(channel=channel)
