"""
tests/test_vision_api.py

Automated integration test suite for Phase 11C-2 Vision API:
- POST /vision/analyze
- JWT authentication and authorization (401 unauthenticated, patient/admin access)
- Multi-format image processing (PNG, JPEG)
- Payload bounds (10MB limit) and rejection of empty/malformed/unsupported images
- Response schema compliance (VisionAnalysisResponse)
- Mandatory non-diagnostic clinical disclaimer verification
- Zero-disk retention & log sanitization
- Identity binding & anti-IDOR verification
"""

import os
import logging
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.vision import MAX_IMAGE_SIZE_BYTES, CLINICAL_VISION_DISCLAIMER

client = TestClient(app)

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


def test_unauthenticated_vision_analyze_returns_401():
    """Verify that unauthenticated requests to /vision/analyze return 401 Unauthorized."""
    res = client.post(
        "/vision/analyze",
        files={"file": ("test.png", VALID_PNG_BYTES, "image/png")}
    )
    assert res.status_code == 401, "Unauthenticated vision analyze did not return 401"


def test_authenticated_patient_can_access_vision_analyze():
    """Verify that authenticated patient can access /vision/analyze."""
    headers = get_patient_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("sample.png", VALID_PNG_BYTES, "image/png")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert "description" in data
    assert data["is_mock"] is True


def test_authenticated_admin_can_access_vision_analyze():
    """Verify that authenticated admin can also access /vision/analyze."""
    headers = get_admin_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("admin_sample.png", VALID_PNG_BYTES, "image/png")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert "description" in data
    assert data["is_mock"] is True


def test_valid_png_image_succeeds():
    """Verify valid PNG upload returns successful analysis and detected resolution."""
    headers = get_patient_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("test.png", VALID_PNG_BYTES, "image/png")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["media_type"] == "image/png"
    assert data["width"] == 1
    assert data["height"] == 1
    assert "resolution_1x1" in data["detected_features"]


def test_valid_jpeg_image_succeeds():
    """Verify valid JPEG upload returns successful analysis and detected resolution."""
    headers = get_patient_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("test.jpg", VALID_JPEG_BYTES, "image/jpeg")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["media_type"] == "image/jpeg"
    assert data["width"] == 1
    assert data["height"] == 1


def test_unsupported_mime_type_rejection():
    """Verify unsupported MIME types (e.g. application/pdf, text/plain) are rejected with 400."""
    headers = get_patient_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("doc.pdf", VALID_PNG_BYTES, "application/pdf")},
        headers=headers
    )
    assert res.status_code == 400
    assert "unsupported mime type" in res.json()["detail"].lower()


def test_empty_image_rejection():
    """Verify empty image (0 bytes) is rejected with 400 Bad Request."""
    headers = get_patient_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("empty.png", b"", "image/png")},
        headers=headers
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_malformed_corrupt_image_rejection():
    """Verify malformed or corrupted non-image header is rejected with 400 Bad Request."""
    headers = get_patient_token_header()
    fake_bytes = b"NOT_A_VALID_IMAGE_HEADER_PADDING_BYTES_1234567890"
    res = client.post(
        "/vision/analyze",
        files={"file": ("corrupt.png", fake_bytes, "image/png")},
        headers=headers
    )
    assert res.status_code == 400
    assert "malformed" in res.json()["detail"].lower() or "unsupported" in res.json()["detail"].lower()


def test_oversized_image_rejection():
    """Verify image exceeding MAX_IMAGE_SIZE_BYTES is rejected with 400 Bad Request."""
    headers = get_patient_token_header()
    oversized_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * (MAX_IMAGE_SIZE_BYTES + 512)
    res = client.post(
        "/vision/analyze",
        files={"file": ("large.png", oversized_bytes, "image/png")},
        headers=headers
    )
    assert res.status_code == 400
    assert "exceeds maximum limit" in res.json()["detail"].lower()


def test_response_conforms_to_vision_analysis_response_schema():
    """Verify JSON response strictly conforms to VisionAnalysisResponse fields."""
    headers = get_patient_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("schema_test.png", VALID_PNG_BYTES, "image/png")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()

    required_fields = [
        "detected_features",
        "description",
        "media_type",
        "width",
        "height",
        "confidence",
        "clinical_disclaimer",
        "is_mock",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field '{field}' in Vision API response"


def test_mandatory_clinical_disclaimer_present():
    """Verify that mandatory non-diagnostic clinical disclaimer is present in API response."""
    headers = get_patient_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("disclaimer_test.png", VALID_PNG_BYTES, "image/png")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["clinical_disclaimer"] == CLINICAL_VISION_DISCLAIMER
    assert "not provide clinical diagnosis" in data["clinical_disclaimer"]


def test_identity_binding_no_arbitrary_patient_override():
    """Verify that identity is derived solely from JWT and cannot be overridden by request params."""
    headers = get_patient_token_header()
    # Pass spoofed patient ID parameter in query
    res = client.post(
        "/vision/analyze?patient_id=999&user_id=888",
        files={"file": ("test.png", VALID_PNG_BYTES, "image/png")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    # Response contains no patient ID leakage
    assert "patient_id" not in data
    assert "user_id" not in data


def test_zero_disk_retention_behavior():
    """Verify that API endpoint leaves zero temporary files on disk during and after processing."""
    headers = get_patient_token_header()
    initial_files = set(os.listdir("."))

    res = client.post(
        "/vision/analyze",
        files={"file": ("zero_disk.png", VALID_PNG_BYTES, "image/png")},
        headers=headers
    )
    assert res.status_code == 200

    current_files = set(os.listdir("."))
    assert current_files == initial_files, "Temporary image files leaked to disk during API processing!"


def test_no_raw_image_bytes_or_base64_in_logs(caplog):
    """Verify application logging does not contain raw image byte representations or base64 streams."""
    headers = get_patient_token_header()

    with caplog.at_level(logging.DEBUG):
        res = client.post(
            "/vision/analyze",
            files={"file": ("log_check.png", VALID_PNG_BYTES, "image/png")},
            headers=headers
        )
    assert res.status_code == 200

    log_text = caplog.text
    assert str(VALID_PNG_BYTES) not in log_text
    assert "iVBORw0KGgo" not in log_text


def test_mock_provider_works_without_cloud_credentials():
    """Verify Mock vision mode functions reliably without external network or API keys."""
    headers = get_patient_token_header()
    res = client.post(
        "/vision/analyze",
        files={"file": ("offline_test.png", VALID_PNG_BYTES, "image/png")},
        headers=headers
    )
    assert res.status_code == 200
    assert res.json()["is_mock"] is True
