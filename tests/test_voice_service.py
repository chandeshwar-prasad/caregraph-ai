"""
tests/test_voice_service.py

Automated unit and integration test suite for Phase 11B-1:
- Voice Service Layer (STT & TTS abstractions)
- MockSTTService and MockTTSService offline execution
- Empty, oversized, and malformed audio rejection
- Provider factory resolution & fallback
- Structured response formats
- Zero-disk persistence verification
- Non-leaking exception translation
"""

import os
import wave
import io
import logging
import pytest
from app.services.voice import (
    BaseSTTService,
    BaseTTSService,
    MockSTTService,
    MockTTSService,
    GroqWhisperSTTService,
    VoiceServiceFactory,
    VoiceError,
    VoiceAuthenticationError,
    VoicePayloadError,
    get_stt_service,
    get_tts_service,
    MAX_AUDIO_SIZE_BYTES,
)


@pytest.fixture
def sample_valid_wav_bytes() -> bytes:
    """Generates a small in-memory valid PCM WAV audio byte string."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 800)  # 800 samples = 0.05s
    return buf.getvalue()


def test_mock_stt_behavior(sample_valid_wav_bytes):
    """Verify MockSTTService correctly processes audio bytes and returns mock transcript."""
    stt = MockSTTService()
    assert stt.is_mock_mode() is True

    result = stt.transcribe(sample_valid_wav_bytes)
    assert isinstance(result, dict)
    assert "transcript" in result
    assert "detected_language" in result
    assert "duration_seconds" in result
    assert result["is_mock"] is True
    assert len(result["transcript"]) > 0


def test_mock_stt_custom_transcript():
    """Verify MockSTTService handles test markers embedded in audio payload."""
    stt = MockSTTService()
    custom_bytes = b"RIFF____WAVEfmt " + b"TRANSCRIPT: I have a severe headache and fever"
    result = stt.transcribe(custom_bytes)
    assert result["transcript"] == "I have a severe headache and fever"
    assert result["is_mock"] is True


def test_mock_tts_behavior():
    """Verify MockTTSService produces valid decodable PCM WAV audio bytes."""
    tts = MockTTSService()
    assert tts.is_mock_mode() is True

    result = tts.synthesize("Your cardiology appointment has been scheduled for tomorrow.")
    assert isinstance(result, dict)
    assert "audio_bytes" in result
    assert "media_type" in result
    assert result["media_type"] == "audio/wav"
    assert result["is_mock"] is True

    # Verify audio is a valid WAV stream that can be opened by the wave module
    audio_stream = io.BytesIO(result["audio_bytes"])
    with wave.open(audio_stream, 'rb') as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000
        assert wav_file.getnframes() > 0


def test_empty_audio_rejection():
    """Verify empty audio (0 bytes) raises VoicePayloadError."""
    stt = MockSTTService()
    with pytest.raises(VoicePayloadError) as exc_info:
        stt.transcribe(b"")
    assert "empty" in str(exc_info.value).lower()


def test_oversized_audio_rejection():
    """Verify audio exceeding MAX_AUDIO_SIZE_BYTES raises VoicePayloadError."""
    stt = MockSTTService()
    # Create fake oversized byte payload > 10MB
    oversized_bytes = b"0" * (MAX_AUDIO_SIZE_BYTES + 1024)

    with pytest.raises(VoicePayloadError) as exc_info:
        stt.transcribe(oversized_bytes)
    assert "exceeds maximum limit" in str(exc_info.value).lower()


def test_malformed_too_small_audio_rejection():
    """Verify audio payload with fewer than 16 bytes is rejected as too small/malformed."""
    stt = MockSTTService()
    with pytest.raises(VoicePayloadError) as exc_info:
        stt.transcribe(b"RIFF123")
    assert "too small" in str(exc_info.value).lower()


def test_tts_empty_and_oversized_text_rejection():
    """Verify TTS service rejects empty text and text exceeding maximum synthesis length."""
    tts = MockTTSService()

    # Empty text
    with pytest.raises(VoicePayloadError) as exc_info:
        tts.synthesize("")
    assert "cannot be empty" in str(exc_info.value).lower()

    # Oversized text (> 2000 chars)
    oversized_text = "A" * 2005
    with pytest.raises(VoicePayloadError) as exc_info:
        tts.synthesize(oversized_text)
    assert "exceeds maximum allowed tts limit" in str(exc_info.value).lower()


def test_provider_factory_behavior():
    """Verify VoiceServiceFactory resolves appropriate service based on config."""
    # 1. Force mock
    stt_mock = VoiceServiceFactory.get_stt_service(force_mock=True)
    assert isinstance(stt_mock, MockSTTService)
    assert stt_mock.is_mock_mode() is True

    # 2. TTS resolution
    tts = VoiceServiceFactory.get_tts_service()
    assert isinstance(tts, BaseTTSService)

    # 3. Global helper functions
    stt_helper = get_stt_service()
    tts_helper = get_tts_service()
    assert isinstance(stt_helper, BaseSTTService)
    assert isinstance(tts_helper, BaseTTSService)


def test_missing_or_invalid_cloud_credentials_handling():
    """Verify that missing or placeholder Groq API key safely falls back to MockSTTService."""
    # Placeholder key -> fallback to mock
    stt_fallback = VoiceServiceFactory.get_stt_service(api_key="your_groq_api_key_here")
    assert isinstance(stt_fallback, MockSTTService)
    assert stt_fallback.is_mock_mode() is True

    # Empty key -> raises VoiceAuthenticationError when directly instantiating GroqWhisperSTTService
    with pytest.raises(VoiceAuthenticationError) as exc_info:
        GroqWhisperSTTService(api_key="")
    assert "cannot be empty" in str(exc_info.value).lower()


def test_structured_stt_response_schema(sample_valid_wav_bytes):
    """Verify STT response dictionary strictly contains all expected fields with correct types."""
    stt = MockSTTService(default_transcript="Test clinical query")
    res = stt.transcribe(sample_valid_wav_bytes)

    assert isinstance(res["transcript"], str)
    assert isinstance(res["detected_language"], str)
    assert isinstance(res["duration_seconds"], float)
    assert isinstance(res["is_mock"], bool)
    assert res["transcript"] == "Test clinical query"


def test_structured_tts_response_schema():
    """Verify TTS response dictionary strictly contains expected audio bytes and media type."""
    tts = MockTTSService()
    res = tts.synthesize("Test synthesis message")

    assert isinstance(res["audio_bytes"], bytes)
    assert isinstance(res["media_type"], str)
    assert isinstance(res["is_mock"], bool)
    assert len(res["audio_bytes"]) > 44  # WAV header is at least 44 bytes


def test_zero_disk_retention_and_no_raw_logging(sample_valid_wav_bytes, caplog, tmp_path):
    """
    Verify that voice processing executes strictly in-memory without creating temporary files
    or logging raw audio bytes or unredacted transcripts.
    """
    initial_files = set(os.listdir("."))

    stt = MockSTTService(default_transcript="Secret patient note")
    tts = MockTTSService()

    with caplog.at_level(logging.DEBUG):
        stt_res = stt.transcribe(sample_valid_wav_bytes)
        tts_res = tts.synthesize("Clinical response audio")

    # 1. Verify no new files created in workspace root
    current_files = set(os.listdir("."))
    assert current_files == initial_files, "Temporary audio files were leaked to disk!"

    # 2. Verify caplog does not contain raw audio bytes or unredacted transcript
    log_text = caplog.text
    assert "Secret patient note" not in log_text
    assert str(sample_valid_wav_bytes) not in log_text
    assert str(tts_res["audio_bytes"]) not in log_text
