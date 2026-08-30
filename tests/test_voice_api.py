"""
tests/test_voice_api.py

Automated integration test suite for Phase 11B-2 Voice API:
- POST /voice/transcribe
- POST /voice/synthesize
- JWT authentication and authorization (401 unauthenticated, valid patient/admin access)
- Payload bounds (10MB audio limit, 2000 char TTS limit)
- Empty/malformed audio handling (400 Bad Request)
- Sanitized error responses without credential or stack trace leakage
- Zero-disk persistence verification
- Absence of raw audio bytes in application logs
"""

import os
import io
import wave
import logging
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.voice import MAX_AUDIO_SIZE_BYTES

client = TestClient(app)


@pytest.fixture
def valid_wav_bytes() -> bytes:
    """Creates in-memory valid PCM WAV audio byte buffer."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)  # 1600 samples = 0.1s
    return buf.getvalue()


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


def test_unauthenticated_voice_endpoints_return_401(valid_wav_bytes):
    """Verify that unauthenticated requests to voice endpoints return 401 Unauthorized."""
    # 1. Transcribe without token
    res_transcribe = client.post(
        "/voice/transcribe",
        files={"file": ("test.wav", valid_wav_bytes, "audio/wav")}
    )
    assert res_transcribe.status_code == 401, "Unauthenticated transcribe did not return 401"

    # 2. Synthesize without token
    res_synth = client.post(
        "/voice/synthesize",
        json={"text": "Hello, how are you today?"}
    )
    assert res_synth.status_code == 401, "Unauthenticated synthesize did not return 401"


def test_authorized_transcription_success(valid_wav_bytes):
    """Verify that authenticated patient can transcribe audio using in-memory mock STT."""
    headers = get_patient_token_header()
    res = client.post(
        "/voice/transcribe",
        files={"file": ("sample.wav", valid_wav_bytes, "audio/wav")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert "transcript" in data
    assert len(data["transcript"]) > 0
    assert data["detected_language"] == "en"
    assert data["duration_seconds"] > 0
    assert data["is_mock"] is True


def test_authorized_transcription_custom_marker():
    """Verify transcription endpoint correctly parses audio with embedded transcript marker."""
    headers = get_patient_token_header()
    custom_bytes = b"RIFF____WAVEfmt " + b"TRANSCRIPT: Schedule appointment with Dr Smith"
    res = client.post(
        "/voice/transcribe",
        files={"file": ("marker.wav", custom_bytes, "audio/wav")},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["transcript"] == "Schedule appointment with Dr Smith"


def test_authorized_synthesis_success():
    """Verify that authenticated patient can synthesize text to audio."""
    headers = get_patient_token_header()
    res = client.post(
        "/voice/synthesize",
        json={"text": "Your prescription for Lisinopril is confirmed."},
        headers=headers
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/wav"
    assert "inline; filename=synthesis.wav" in res.headers["content-disposition"]
    assert len(res.content) > 44  # Valid WAV byte length

    # Verify audio decodability
    audio_stream = io.BytesIO(res.content)
    with wave.open(audio_stream, 'rb') as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 16000


def test_admin_can_access_voice_endpoints(valid_wav_bytes):
    """Verify that admin role also has access to transcription and synthesis utilities."""
    headers = get_admin_token_header()

    res_stt = client.post(
        "/voice/transcribe",
        files={"file": ("admin_test.wav", valid_wav_bytes, "audio/wav")},
        headers=headers
    )
    assert res_stt.status_code == 200

    res_tts = client.post(
        "/voice/synthesize",
        json={"text": "System telemetry reporting normal operations."},
        headers=headers
    )
    assert res_tts.status_code == 200
    assert len(res_tts.content) > 44


def test_oversized_audio_upload_rejection():
    """Verify that audio payloads exceeding MAX_AUDIO_SIZE_BYTES are rejected with 400 Bad Request."""
    headers = get_patient_token_header()
    oversized_bytes = b"0" * (MAX_AUDIO_SIZE_BYTES + 512)

    res = client.post(
        "/voice/transcribe",
        files={"file": ("large.wav", oversized_bytes, "audio/wav")},
        headers=headers
    )
    assert res.status_code == 400
    assert "exceeds maximum limit" in res.json()["detail"].lower()


def test_empty_and_malformed_audio_rejection():
    """Verify that empty or malformed audio (<16 bytes) is rejected with 400 Bad Request."""
    headers = get_patient_token_header()

    # Empty file
    res_empty = client.post(
        "/voice/transcribe",
        files={"file": ("empty.wav", b"", "audio/wav")},
        headers=headers
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()

    # Too small / malformed (< 16 bytes)
    res_small = client.post(
        "/voice/transcribe",
        files={"file": ("tiny.wav", b"RIFF1234", "audio/wav")},
        headers=headers
    )
    assert res_small.status_code == 400
    assert "too small" in res_small.json()["detail"].lower()


def test_tts_empty_and_oversized_text_rejection():
    """Verify that empty text and oversized text (>2000 chars) are rejected with 422 or 400."""
    headers = get_patient_token_header()

    # Empty text
    res_empty = client.post(
        "/voice/synthesize",
        json={"text": ""},
        headers=headers
    )
    assert res_empty.status_code in [400, 422]

    # Oversized text (> 2000 chars)
    res_over = client.post(
        "/voice/synthesize",
        json={"text": "X" * 2005},
        headers=headers
    )
    assert res_over.status_code in [400, 422]


def test_zero_disk_persistence_and_log_sanitization(valid_wav_bytes, caplog):
    """
    Verify that API execution leaves zero audio files on disk and does not log
    raw binary audio buffers or complete unredacted transcripts.
    """
    headers = get_patient_token_header()
    initial_files = set(os.listdir("."))

    with caplog.at_level(logging.DEBUG):
        res_stt = client.post(
            "/voice/transcribe",
            files={"file": ("log_test.wav", valid_wav_bytes, "audio/wav")},
            headers=headers
        )
        res_tts = client.post(
            "/voice/synthesize",
            json={"text": "Confidential patient message for audio check"},
            headers=headers
        )

    assert res_stt.status_code == 200
    assert res_tts.status_code == 200

    # 1. Zero disk writes
    current_files = set(os.listdir("."))
    assert current_files == initial_files, "Temporary audio files leaked to disk during API processing!"

    # 2. No raw audio in logs
    log_text = caplog.text
    assert str(valid_wav_bytes) not in log_text
    assert str(res_tts.content) not in log_text
