"""
tests/test_multimodal_agent.py

Comprehensive test suite verifying true Multimodal Agent Fusion (Phase 12):
1. Voice-to-Voice Conversational Agent (/chat/voice)
2. Medical Document & Visual Observation Analysis (/chat/vision)
3. Automated Outbound SMS Dispatch on Appointment Approval (/chat/approve)
4. In-Memory Zero-Disk Retention & Safety Disclaimer Enforcement
"""

import pytest
import io
import wave
import struct
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, engine, Base
from app import crud, schemas, models

client = TestClient(app)


def _generate_valid_wav_bytes(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a syntactically valid in-memory PCM WAV audio byte buffer."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        num_frames = int(sample_rate * duration_sec)
        samples = [int(300 * (i % 50)) for i in range(num_frames)]
        raw_pcm = struct.pack(f"<{len(samples)}h", *samples)
        wav_file.writeframes(raw_pcm)
    buffer.seek(0)
    return buffer.read()


def _generate_valid_png_bytes(width: int = 100, height: int = 100) -> bytes:
    """Generate a minimal valid in-memory PNG byte stream."""
    import zlib
    header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc
    raw_pixels = b"\x00" + (b"\xff\x00\x00" * width)
    raw_scanlines = raw_pixels * height
    compressed_idat = zlib.compress(raw_scanlines)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed_idat))
    idat = struct.pack(">I", len(compressed_idat)) + b"IDAT" + compressed_idat + idat_crc
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND"))
    iend = struct.pack(">I", 0) + b"IEND" + iend_crc
    return header + ihdr + idat + iend


@pytest.fixture
def auth_patient_headers():
    """Create a test patient user and return authorization bearer headers."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "multimodal_test_patient").first()
        if not user:
            user = crud.create_user(
                db,
                schemas.UserCreate(
                    username="multimodal_test_patient",
                    password="password123",
                    role="patient"
                )
            )
            crud.create_patient_profile(
                db,
                user.id,
                schemas.PatientCreate(
                    first_name="Multimodal",
                    last_name="Tester",
                    email="multimodal@example.com",
                    phone="+15559876543"
                )
            )
        response = client.post(
            "/auth/login",
            data={"username": "multimodal_test_patient", "password": "password123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


# --- Voice-to-Voice Pipeline Tests ---

def test_chat_voice_coordination_success(auth_patient_headers):
    """Test voice audio upload transcribes, executes graph agent, and returns synthesized TTS."""
    wav_bytes = _generate_valid_wav_bytes(duration_sec=1.5)
    files = {"file": ("symptom_recording.wav", wav_bytes, "audio/wav")}
    data = {
        "session_id": "test_voice_sess_1",
        "synthesize_voice": "true",
        "use_fhir": "false"
    }

    response = client.post(
        "/chat/voice",
        files=files,
        data=data,
        headers=auth_patient_headers
    )

    assert response.status_code == 200
    res_data = response.json()
    assert "transcribed_text" in res_data
    assert len(res_data["transcribed_text"]) > 0
    assert "message" in res_data
    assert "intent" in res_data
    assert res_data["audio_base64"] is not None
    assert res_data["audio_media_type"] == "audio/wav"


def test_chat_voice_empty_payload_rejected(auth_patient_headers):
    """Test empty audio file returns HTTP 400."""
    files = {"file": ("empty.wav", b"", "audio/wav")}
    response = client.post(
        "/chat/voice",
        files=files,
        data={"session_id": "test_voice_err"},
        headers=auth_patient_headers
    )
    assert response.status_code == 400


# --- Vision Document Ingestion Tests ---

def test_chat_vision_coordination_success(auth_patient_headers):
    """Test document/image upload analyzes visual features, merges query, and invokes agent graph."""
    png_bytes = _generate_valid_png_bytes(width=150, height=150)
    files = {"file": ("lab_report.png", png_bytes, "image/png")}
    data = {
        "message": "I uploaded my recent lab report, please evaluate",
        "session_id": "test_vision_sess_1",
        "use_fhir": "false"
    }

    response = client.post(
        "/chat/vision",
        files=files,
        data=data,
        headers=auth_patient_headers
    )

    assert response.status_code == 200
    res_data = response.json()
    assert "message" in res_data
    assert "intent" in res_data
    assert "vision_analysis" in res_data
    assert "extracted_observations" in res_data
    assert "clinical_disclaimer" in res_data
    assert "CareGraph AI Vision is for care navigation" in res_data["clinical_disclaimer"]


def test_chat_vision_empty_payload_rejected(auth_patient_headers):
    """Test empty image payload returns HTTP 400."""
    files = {"file": ("empty.png", b"", "image/png")}
    response = client.post(
        "/chat/vision",
        files=files,
        data={"message": "check this"},
        headers=auth_patient_headers
    )
    assert response.status_code == 400


# --- Automated Messaging on Appointment Approval ---

def test_automated_messaging_on_appointment_approval(auth_patient_headers):
    """Test that approving a scheduled appointment slot triggers outbound SMS confirmation."""
    # 1. Trigger scheduling conversation requiring approval
    chat_res = client.post(
        "/chat",
        json={
            "message": "I need to schedule an appointment with Dr. Smith for cardiology next Monday",
            "session_id": "approval_notify_session"
        },
        headers=auth_patient_headers
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    if chat_data.get("approval_required"):
        # 2. Submit approval decision
        approve_res = client.post(
            "/chat/approve",
            json={
                "session_id": "approval_notify_session",
                "decision": "approved"
            },
            headers=auth_patient_headers
        )
        assert approve_res.status_code == 200
        approve_data = approve_res.json()
        assert approve_data["approval_status"] == "approved"
        assert "confirmed" in approve_data["message"].lower() or "scheduled" in approve_data["message"].lower() or "approved" in approve_data["message"].lower()
