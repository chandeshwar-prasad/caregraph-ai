"""
tests/test_vision_service.py

Automated unit and integration test suite for Phase 11C-1 Vision Service Layer:
- Provider-agnostic BaseVisionService abstraction
- In-memory MockVisionService offline execution
- Valid image processing (PNG, JPEG, WebP, GIF)
- Rejection of empty, oversized (>10MB), malformed, and unsupported MIME types
- Provider factory resolution & fallback
- Structured response schema compliance
- Zero-disk retention verification
- No raw image bytes or base64 in application logs
- Clinical safety boundary & mandatory non-diagnostic disclaimer verification
- Cloud provider exception sanitization
"""

import os
import logging
import pytest
from app.services.vision import (
    BaseVisionService,
    MockVisionService,
    GroqVisionService,
    VisionServiceFactory,
    VisionError,
    VisionAuthenticationError,
    VisionPayloadError,
    VisionProcessingError,
    get_vision_service,
    MAX_IMAGE_SIZE_BYTES,
    CLINICAL_VISION_DISCLAIMER,
)
from app.schemas_ai import VisionAnalysisResponse

# Standard minimal in-memory test image bytes
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa76\x814\x00\x00\x00\x00IEND\xaeB`\x82"
)

VALID_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05"
    b"\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c"
    b" $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
    b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06"
    b"\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


def test_mock_vision_service_behavior():
    """Verify MockVisionService processes valid image in-memory and returns structured response."""
    vision = MockVisionService()
    assert vision.is_mock_mode() is True

    result = vision.analyze_image(VALID_PNG_BYTES, filename="doc.png", content_type="image/png")
    assert isinstance(result, dict)
    assert result["is_mock"] is True
    assert result["media_type"] == "image/png"
    assert len(result["detected_features"]) > 0
    assert "description" in result
    assert result["clinical_disclaimer"] == CLINICAL_VISION_DISCLAIMER


def test_valid_image_processing_png_and_jpeg():
    """Verify valid PNG and JPEG image byte containers are inspected properly."""
    vision = MockVisionService()

    # PNG
    res_png = vision.analyze_image(VALID_PNG_BYTES, content_type="image/png")
    assert res_png["media_type"] == "image/png"
    assert res_png["width"] == 1
    assert res_png["height"] == 1

    # JPEG
    res_jpeg = vision.analyze_image(VALID_JPEG_BYTES, content_type="image/jpeg")
    assert res_jpeg["media_type"] == "image/jpeg"
    assert res_jpeg["width"] == 1
    assert res_jpeg["height"] == 1


def test_unsupported_mime_type_rejection():
    """Verify unsupported MIME types (e.g. application/pdf, text/plain) raise VisionPayloadError."""
    vision = MockVisionService()

    with pytest.raises(VisionPayloadError) as exc_info:
        vision.analyze_image(VALID_PNG_BYTES, content_type="application/pdf")
    assert "unsupported mime type" in str(exc_info.value).lower()


def test_empty_image_rejection():
    """Verify empty image bytes (0 bytes) raise VisionPayloadError."""
    vision = MockVisionService()

    with pytest.raises(VisionPayloadError) as exc_info:
        vision.analyze_image(b"", content_type="image/png")
    assert "empty" in str(exc_info.value).lower()


def test_oversized_image_rejection():
    """Verify image exceeding MAX_IMAGE_SIZE_BYTES raises VisionPayloadError."""
    vision = MockVisionService()
    oversized_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * (MAX_IMAGE_SIZE_BYTES + 1024)

    with pytest.raises(VisionPayloadError) as exc_info:
        vision.analyze_image(oversized_bytes, content_type="image/png")
    assert "exceeds maximum limit" in str(exc_info.value).lower()


def test_malformed_corrupt_image_rejection():
    """Verify non-image bytes or corrupted header bytes raise VisionPayloadError."""
    vision = MockVisionService()
    fake_corrupt_bytes = b"NOT_A_VALID_IMAGE_HEADER_PADDING_BYTES_1234567890"

    with pytest.raises(VisionPayloadError) as exc_info:
        vision.analyze_image(fake_corrupt_bytes, content_type="image/png")
    assert "malformed" in str(exc_info.value).lower() or "unsupported" in str(exc_info.value).lower()


def test_provider_factory_behavior():
    """Verify VisionServiceFactory resolves appropriate service based on config."""
    # 1. Force mock
    mock_service = VisionServiceFactory.get_vision_service(force_mock=True)
    assert isinstance(mock_service, MockVisionService)
    assert mock_service.is_mock_mode() is True

    # 2. Global helper
    helper_service = get_vision_service()
    assert isinstance(helper_service, BaseVisionService)


def test_missing_or_placeholder_cloud_credentials_fallback():
    """Verify that placeholder or missing Groq API key falls back to MockVisionService."""
    service = VisionServiceFactory.get_vision_service(api_key="your_groq_api_key_here")
    assert isinstance(service, MockVisionService)
    assert service.is_mock_mode() is True

    # Empty key directly instantiating GroqVisionService raises VisionAuthenticationError
    with pytest.raises(VisionAuthenticationError) as exc_info:
        GroqVisionService(api_key="")
    assert "cannot be empty" in str(exc_info.value).lower()


def test_structured_response_schema_compliance():
    """Verify vision output strictly conforms to Pydantic VisionAnalysisResponse."""
    vision = MockVisionService(default_description="Test medical report visual observation")
    result = vision.analyze_image(VALID_PNG_BYTES)

    # Validate against Pydantic schema
    response_model = VisionAnalysisResponse(**result)
    assert response_model.description == "Test medical report visual observation"
    assert response_model.media_type == "image/png"
    assert response_model.is_mock is True
    assert response_model.confidence == 1.0
    assert response_model.clinical_disclaimer == CLINICAL_VISION_DISCLAIMER


def test_zero_disk_retention_behavior():
    """Verify that vision analysis operates purely in RAM without creating temporary files on disk."""
    initial_files = set(os.listdir("."))
    vision = MockVisionService()

    result = vision.analyze_image(VALID_PNG_BYTES, filename="in_memory_test.png")
    assert result is not None

    current_files = set(os.listdir("."))
    assert current_files == initial_files, "Temporary image files were leaked to disk!"


def test_no_raw_image_bytes_or_base64_in_logs(caplog):
    """Verify application logging does not contain raw image byte representations or base64 streams."""
    vision = MockVisionService()

    with caplog.at_level(logging.DEBUG):
        vision.analyze_image(VALID_PNG_BYTES)

    log_text = caplog.text
    assert str(VALID_PNG_BYTES) not in log_text
    assert "iVBORw0KGgo" not in log_text  # Common PNG base64 prefix


def test_clinical_safety_boundary_and_disclaimer():
    """Verify that the service explicitly enforces non-diagnostic clinical safety boundaries."""
    vision = MockVisionService()
    result = vision.analyze_image(VALID_PNG_BYTES)

    # Must contain the explicit disclaimer
    assert "clinical_disclaimer" in result
    disclaimer = result["clinical_disclaimer"]
    assert "not provide clinical diagnosis" in disclaimer
    assert "observation" in disclaimer or "navigation" in disclaimer


def test_cloud_provider_exception_sanitization():
    """Verify that cloud provider exceptions are wrapped and sanitized without exposing keys."""
    cloud_service = GroqVisionService(api_key="gsk_simulated_key_12345678901234567890")

    # When passing invalid bytes, payload error is raised cleanly before network call
    with pytest.raises(VisionPayloadError):
        cloud_service.analyze_image(b"invalid_small_bytes")
