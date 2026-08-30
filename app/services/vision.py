"""
app/services/vision.py

Provider-agnostic Vision Service Layer for CareGraph AI.
Provides:
1. BaseVisionService abstract interface.
2. In-memory MockVisionService for deterministic offline, testing, and CI execution.
3. Cloud vision provider adapter (GroqVisionService).
4. VisionServiceFactory for dynamic provider resolution.
5. Strict image payload validation, magic-byte inspection, zero-disk retention,
   and explicit non-diagnostic clinical safety boundaries.
"""

import os
import base64
import struct
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("caregraph.vision")

# Validation Constraints
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB maximum image size
MIN_IMAGE_SIZE_BYTES = 32                # Minimum valid image container header
SUPPORTED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
}

CLINICAL_VISION_DISCLAIMER = (
    "CareGraph AI Vision is for care navigation and symptom/document observation assistance only, "
    "and does not provide clinical diagnosis, medical evaluation, or diagnostic decisions."
)


# --- Exception Hierarchy ---

class VisionError(Exception):
    """Base exception for vision operations."""
    pass


class VisionAuthenticationError(VisionError):
    """Authentication or API key misconfiguration for vision provider."""
    pass


class VisionConnectionError(VisionError):
    """Connection, network, or timeout error with vision provider."""
    pass


class VisionPayloadError(VisionError):
    """Empty, oversized, unsupported, or corrupt image payload error."""
    pass


class VisionProcessingError(VisionError):
    """Error during vision feature extraction or parsing."""
    pass


# --- Image Payload & Header Inspection ---

def inspect_image_header(image_bytes: bytes) -> Tuple[str, Optional[int], Optional[int]]:
    """
    Validates magic bytes and inspects dimensions for standard image formats in-memory.
    Returns (detected_mime_type, width, height).
    Raises VisionPayloadError if format is invalid or corrupt.
    """
    if not image_bytes or len(image_bytes) < MIN_IMAGE_SIZE_BYTES:
        raise VisionPayloadError(f"Image payload too small ({len(image_bytes) if image_bytes else 0} bytes).")

    # 1. PNG Header: \x89PNG\r\n\x1a\n
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        try:
            width, height = struct.unpack(">II", image_bytes[16:24])
            return "image/png", width, height
        except Exception:
            return "image/png", None, None

    # 2. JPEG Header: \xff\xd8\xff
    elif image_bytes.startswith(b"\xff\xd8\xff"):
        # Extract dimensions from SOF markers
        try:
            offset = 2
            size = len(image_bytes)
            width, height = None, None
            while offset < size - 8:
                if image_bytes[offset] != 0xFF:
                    offset += 1
                    continue
                marker = image_bytes[offset + 1]
                if marker in [0xC0, 0xC1, 0xC2, 0xC3]:  # SOF markers
                    height, width = struct.unpack(">HH", image_bytes[offset + 5:offset + 9])
                    break
                elif marker in [0xDA, 0xD9]:  # SOS or EOI
                    break
                else:
                    length = struct.unpack(">H", image_bytes[offset + 2:offset + 4])[0]
                    offset += 2 + length
            return "image/jpeg", width, height
        except Exception:
            return "image/jpeg", None, None

    # 3. GIF Header: GIF87a or GIF89a
    elif image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        try:
            width, height = struct.unpack("<HH", image_bytes[6:10])
            return "image/gif", width, height
        except Exception:
            return "image/gif", None, None

    # 4. WebP Header: RIFF....WEBP
    elif image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        try:
            if image_bytes[12:16] == b"VP8 ":
                width, height = struct.unpack("<HH", image_bytes[26:30])
                width &= 0x3FFF
                height &= 0x3FFF
                return "image/webp", width, height
            elif image_bytes[12:16] == b"VP8L":
                b0, b1, b2, b3 = struct.unpack("<BBBB", image_bytes[21:25])
                width = 1 + (((b1 & 0x3F) << 8) | b0)
                height = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
                return "image/webp", width, height
            return "image/webp", None, None
        except Exception:
            return "image/webp", None, None

    raise VisionPayloadError("Unsupported or malformed image format. Magic bytes do not match PNG, JPEG, GIF, or WebP.")


def validate_image_payload(image_bytes: bytes, content_type: Optional[str] = None) -> Tuple[str, Optional[int], Optional[int]]:
    """
    Comprehensive in-memory validation of image bytes:
    1. Null / emptiness check
    2. Size boundaries (MIN_IMAGE_SIZE_BYTES <= size <= MAX_IMAGE_SIZE_BYTES)
    3. MIME type header verification
    4. Magic-byte verification and dimension parsing
    """
    if image_bytes is None:
        raise VisionPayloadError("Image payload cannot be None.")

    size = len(image_bytes)
    if size == 0:
        raise VisionPayloadError("Image payload is empty (0 bytes).")

    if size < MIN_IMAGE_SIZE_BYTES:
        raise VisionPayloadError(f"Image payload too small ({size} bytes). Minimum size is {MIN_IMAGE_SIZE_BYTES} bytes.")

    if size > MAX_IMAGE_SIZE_BYTES:
        raise VisionPayloadError(
            f"Image payload exceeds maximum limit of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB "
            f"(received {size / (1024 * 1024):.2f}MB)."
        )

    if content_type:
        norm_type = content_type.lower().split(";")[0].strip()
        if norm_type not in SUPPORTED_MIME_TYPES:
            raise VisionPayloadError(f"Unsupported MIME type '{content_type}'. Supported: {', '.join(sorted(SUPPORTED_MIME_TYPES))}.")

    # Verify actual container bytes match supported image formats
    detected_mime, width, height = inspect_image_header(image_bytes)
    return detected_mime, width, height


# --- Abstract Base Vision Service ---

class BaseVisionService(ABC):
    """Abstract interface for Vision providers."""

    @abstractmethod
    def analyze_image(
        self,
        image_bytes: bytes,
        filename: str = "image.png",
        content_type: str = "image/png",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes in-memory image bytes for care coordination and document overview.
        Must return a structured dictionary conforming to VisionAnalysisResponse:
        {
            "detected_features": List[str],
            "description": str,
            "media_type": str,
            "width": Optional[int],
            "height": Optional[int],
            "confidence": float,
            "clinical_disclaimer": str,
            "is_mock": bool
        }
        """
        pass

    @abstractmethod
    def is_mock_mode(self) -> bool:
        """Returns True if this provider is a mock/offline implementation."""
        pass


# --- Mock Vision Implementation ---

class MockVisionService(BaseVisionService):
    """
    Deterministic in-memory Mock Vision Provider for offline tests, local dev, and CI.
    Zero external network calls, zero credentials required, strictly non-diagnostic.
    """

    def __init__(self, default_description: Optional[str] = None):
        self.default_description = default_description

    def analyze_image(
        self,
        image_bytes: bytes,
        filename: str = "image.png",
        content_type: str = "image/png",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        detected_mime, width, height = validate_image_payload(image_bytes, content_type)

        # Non-diagnostic feature detection simulation based on container properties
        detected_features = ["valid_image_container", "care_navigation_visual_input"]
        if width and height:
            detected_features.append(f"resolution_{width}x{height}")
            if width >= 800 or height >= 800:
                detected_features.append("high_resolution_document_layout")

        # Custom test marker support
        description = (
            self.default_description
            or (prompt and f"Visual observation for query: '{prompt}'")
            or "Visual analysis completed: High-contrast document/image layout observed. No autonomous clinical diagnosis performed."
        )

        return {
            "detected_features": detected_features,
            "description": description,
            "media_type": detected_mime,
            "width": width,
            "height": height,
            "confidence": 1.0,
            "clinical_disclaimer": CLINICAL_VISION_DISCLAIMER,
            "is_mock": True,
        }

    def is_mock_mode(self) -> bool:
        return True


# --- Cloud Vision Provider (Groq Vision Adapter) ---

class GroqVisionService(BaseVisionService):
    """
    Cloud Vision Provider using Groq Vision models (e.g. llama-3.2-11b-vision-preview).
    Strictly bounded to care coordination observations; disallows autonomous clinical diagnosis.
    """

    def __init__(self, api_key: str, model: str = "llama-3.2-11b-vision-preview"):
        if not api_key or not api_key.strip():
            raise VisionAuthenticationError("Groq API key cannot be empty for vision service.")
        self.api_key = api_key.strip()
        self.model = model

        try:
            import groq
            self.client = groq.Groq(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Groq client for Vision: {e}")
            raise VisionError("Failed to initialize Groq SDK for vision analysis.")

    def analyze_image(
        self,
        image_bytes: bytes,
        filename: str = "image.png",
        content_type: str = "image/png",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        detected_mime, width, height = validate_image_payload(image_bytes, content_type)

        import groq

        # Convert in-memory bytes to data URL (zero disk retention)
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{detected_mime};base64,{b64_img}"

        system_instruction = (
            "You are a care navigation visual observer. Describe visible document elements, labels, "
            "or visual structures to assist in care coordination. "
            "CRITICAL SAFETY RULE: You are NOT a doctor and MUST NOT issue medical diagnoses, prescriptions, "
            "or autonomous clinical recommendations."
        )
        user_query = prompt or "Describe the visual features and layout in this image for healthcare care coordination."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_query},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ]
                    }
                ],
                max_tokens=500
            )

            raw_text = response.choices[0].message.content or ""
            return {
                "detected_features": ["cloud_vision_analyzed", "care_coordination_observation"],
                "description": raw_text.strip(),
                "media_type": detected_mime,
                "width": width,
                "height": height,
                "confidence": 0.95,
                "clinical_disclaimer": CLINICAL_VISION_DISCLAIMER,
                "is_mock": False,
            }

        except groq.AuthenticationError:
            raise VisionAuthenticationError("Invalid Groq API key or vision authentication failure.")
        except (groq.APITimeoutError, groq.APIConnectionError):
            raise VisionConnectionError("Connection or timeout error while contacting Groq Vision API.")
        except groq.RateLimitError:
            raise VisionError("Groq Vision API rate limit exceeded.")
        except groq.APIError as e:
            raise VisionError(f"Groq Vision API error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Groq Vision analysis: {type(e).__name__}")
            raise VisionProcessingError("Vision image analysis failed.")

    def is_mock_mode(self) -> bool:
        return False


# --- Vision Service Factory ---

class VisionServiceFactory:
    """Factory for instantiating and resolving Vision providers."""

    @staticmethod
    def get_vision_service(
        api_key: Optional[str] = None,
        model: Optional[str] = "llama-3.2-11b-vision-preview",
        force_mock: bool = False
    ) -> BaseVisionService:
        """
        Resolves Vision provider:
        - If force_mock is True, returns MockVisionService.
        - If GROQ_API_KEY is available and valid, returns GroqVisionService.
        - Otherwise, gracefully falls back to MockVisionService.
        """
        if force_mock:
            return MockVisionService()

        groq_key = api_key or os.getenv("GROQ_API_KEY", "").strip()
        is_placeholder = not groq_key or groq_key.startswith("your_") or "placeholder" in groq_key.lower()

        if is_placeholder:
            return MockVisionService()

        try:
            return GroqVisionService(api_key=groq_key, model=model or "llama-3.2-11b-vision-preview")
        except Exception as e:
            logger.warning(f"Failed to initialize GroqVisionService ({e}). Falling back to MockVisionService.")
            return MockVisionService()


# Global convenience helper function
def get_vision_service(api_key: Optional[str] = None, model: Optional[str] = None) -> BaseVisionService:
    return VisionServiceFactory.get_vision_service(api_key=api_key, model=model)
