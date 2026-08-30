"""
app/services/voice.py

Provider-agnostic Voice Service Layer for CareGraph AI.
Provides:
1. BaseSTTService and BaseTTSService abstract interfaces.
2. In-memory MockSTTService and MockTTSService for deterministic offline & CI operation.
3. GroqWhisperSTTService for sub-second cloud speech-to-text.
4. VoiceServiceFactory for dynamic provider resolution.
5. Strict zero-disk retention, payload validation, and decoupled error translation.
"""

import os
import io
import wave
import struct
import math
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger("caregraph.voice")

# Configuration Constants
MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB maximum audio payload limit
MAX_TEXT_SYNTHESIS_LENGTH = 2000          # 2000 characters maximum for TTS


# --- Decoupled Voice Exception Hierarchy ---

class VoiceError(Exception):
    """Base exception for voice service operations."""
    pass


class VoiceAuthenticationError(VoiceError):
    """Authentication or API key misconfiguration."""
    pass


class VoiceConnectionError(VoiceError):
    """Connection, network, or timeout error with voice provider."""
    pass


class VoicePayloadError(VoiceError):
    """Empty, oversized, or malformed audio payload error."""
    pass


# --- Abstract Service Interfaces ---

class BaseSTTService(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav"
    ) -> Dict[str, Any]:
        """
        Transcribes in-memory audio bytes into text.
        Must return a structured dictionary:
        {
            "transcript": str,
            "detected_language": str,
            "duration_seconds": float,
            "is_mock": bool
        }
        """
        pass

    @abstractmethod
    def is_mock_mode(self) -> bool:
        """Returns True if this provider is a mock/offline implementation."""
        pass


class BaseTTSService(ABC):
    """Abstract interface for Text-to-Speech providers."""

    @abstractmethod
    def synthesize(self, text: str, voice_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Synthesizes safe text into in-memory audio bytes.
        Must return a structured dictionary:
        {
            "audio_bytes": bytes,
            "media_type": str,
            "is_mock": bool
        }
        """
        pass

    @abstractmethod
    def is_mock_mode(self) -> bool:
        """Returns True if this provider is a mock/offline implementation."""
        pass


# --- Payload Validation Helper ---

def validate_audio_payload(audio_bytes: bytes) -> None:
    """
    Validates audio byte constraints:
    - Must not be None
    - Must be non-empty (at least 16 bytes for valid container headers)
    - Must not exceed MAX_AUDIO_SIZE_BYTES
    """
    if audio_bytes is None:
        raise VoicePayloadError("Audio payload cannot be None.")

    size = len(audio_bytes)
    if size == 0:
        raise VoicePayloadError("Audio payload is empty (0 bytes).")

    if size < 16:
        raise VoicePayloadError(f"Audio payload is too small ({size} bytes) to contain a valid audio stream.")

    if size > MAX_AUDIO_SIZE_BYTES:
        raise VoicePayloadError(
            f"Audio payload exceeds maximum limit of {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB "
            f"(received {size / (1024 * 1024):.2f}MB)."
        )


def _generate_synthetic_wav_bytes(duration_sec: float = 0.5, frequency: float = 440.0) -> bytes:
    """Generates valid minimal in-memory PCM WAV audio bytes for mock synthesis."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)       # Mono
        wav_file.setsampwidth(2)      # 16-bit
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            value = int(32767.0 * 0.1 * math.sin(2.0 * math.pi * frequency * (i / sample_rate)))
            frames.extend(struct.pack('<h', value))
        wav_file.writeframes(frames)

    return buf.getvalue()


# --- Mock Implementations (Deterministic Offline & CI) ---

class MockSTTService(BaseSTTService):
    """In-memory mock STT service for unit testing and offline development."""

    def __init__(self, default_transcript: Optional[str] = None):
        self.default_transcript = default_transcript

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav"
    ) -> Dict[str, Any]:
        validate_audio_payload(audio_bytes)

        # Check if the audio contains an explicit test transcript encoded in bytes
        if b"TRANSCRIPT:" in audio_bytes:
            try:
                marker_idx = audio_bytes.index(b"TRANSCRIPT:") + len(b"TRANSCRIPT:")
                custom_transcript = audio_bytes[marker_idx:].decode("utf-8", errors="ignore").strip()
                if custom_transcript:
                    return {
                        "transcript": custom_transcript,
                        "detected_language": "en",
                        "duration_seconds": 2.5,
                        "is_mock": True,
                    }
            except Exception:
                pass

        transcript = (
            self.default_transcript
            or "I would like to check available appointment slots with a cardiologist tomorrow morning."
        )

        return {
            "transcript": transcript,
            "detected_language": "en",
            "duration_seconds": 2.0,
            "is_mock": True,
        }

    def is_mock_mode(self) -> bool:
        return True


class MockTTSService(BaseTTSService):
    """In-memory mock TTS service for generating valid decodable audio bytes."""

    def synthesize(self, text: str, voice_id: Optional[str] = None) -> Dict[str, Any]:
        if not text or not text.strip():
            raise VoicePayloadError("Text to synthesize cannot be empty.")

        if len(text) > MAX_TEXT_SYNTHESIS_LENGTH:
            raise VoicePayloadError(
                f"Text length ({len(text)} chars) exceeds maximum allowed TTS limit "
                f"({MAX_TEXT_SYNTHESIS_LENGTH} chars)."
            )

        audio_bytes = _generate_synthetic_wav_bytes(duration_sec=0.25, frequency=440.0)

        return {
            "audio_bytes": audio_bytes,
            "media_type": "audio/wav",
            "is_mock": True,
        }

    def is_mock_mode(self) -> bool:
        return True


# --- Cloud Implementations (Groq Whisper) ---

class GroqWhisperSTTService(BaseSTTService):
    """Cloud STT service using Groq Whisper (e.g. whisper-large-v3)."""

    def __init__(self, api_key: str, model: str = "whisper-large-v3"):
        if not api_key or not api_key.strip():
            raise VoiceAuthenticationError("Groq API key cannot be empty.")
        self.api_key = api_key.strip()
        self.model = model

        try:
            import groq
            self.client = groq.Groq(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Groq client for Whisper STT: {e}")
            raise VoiceError("Failed to initialize Groq SDK for speech transcription.")

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav"
    ) -> Dict[str, Any]:
        validate_audio_payload(audio_bytes)

        import groq

        try:
            # Pass in-memory audio tuple directly to Groq Whisper
            file_payload = (filename or "audio.wav", audio_bytes, content_type or "audio/wav")
            response = self.client.audio.transcriptions.create(
                file=file_payload,
                model=self.model,
                response_format="verbose_json"
            )

            transcript = getattr(response, "text", "") or ""
            language = getattr(response, "language", "en") or "en"
            duration = getattr(response, "duration", 0.0) or 0.0

            return {
                "transcript": transcript.strip(),
                "detected_language": language,
                "duration_seconds": round(float(duration), 2) if duration else 0.0,
                "is_mock": False,
            }

        except groq.AuthenticationError:
            raise VoiceAuthenticationError("Invalid Groq API key or voice authentication failure.")
        except (groq.APITimeoutError, groq.APIConnectionError):
            raise VoiceConnectionError("Connection or timeout error while contacting Groq Whisper STT.")
        except groq.RateLimitError:
            raise VoiceError("Groq Whisper STT rate limit exceeded.")
        except groq.APIError as e:
            raise VoiceError(f"Groq Whisper STT API error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Groq Whisper transcription: {type(e).__name__}")
            raise VoiceError("Speech transcription failed.")

    def is_mock_mode(self) -> bool:
        return False


# --- Voice Service Factory ---

class VoiceServiceFactory:
    """Factory for instantiating and resolving STT and TTS service providers."""

    @staticmethod
    def get_stt_service(
        api_key: Optional[str] = None,
        model: Optional[str] = "whisper-large-v3",
        force_mock: bool = False
    ) -> BaseSTTService:
        """
        Resolves STT provider:
        - If force_mock is True, returns MockSTTService.
        - If GROQ_API_KEY is available and valid, returns GroqWhisperSTTService.
        - Otherwise, gracefully falls back to MockSTTService.
        """
        if force_mock:
            return MockSTTService()

        groq_key = api_key or os.getenv("GROQ_API_KEY", "").strip()
        is_placeholder = not groq_key or groq_key.startswith("your_") or "placeholder" in groq_key.lower()

        if is_placeholder:
            return MockSTTService()

        try:
            return GroqWhisperSTTService(api_key=groq_key, model=model or "whisper-large-v3")
        except Exception as e:
            logger.warning(f"Failed to initialize GroqWhisperSTTService ({e}). Falling back to MockSTTService.")
            return MockSTTService()

    @staticmethod
    def get_tts_service(force_mock: bool = True) -> BaseTTSService:
        """
        Resolves TTS provider:
        Returns in-memory MockTTSService for local and mock execution.
        """
        return MockTTSService()


# Global convenience helper functions
def get_stt_service(api_key: Optional[str] = None, model: Optional[str] = None) -> BaseSTTService:
    return VoiceServiceFactory.get_stt_service(api_key=api_key, model=model)

def get_tts_service() -> BaseTTSService:
    return VoiceServiceFactory.get_tts_service()
