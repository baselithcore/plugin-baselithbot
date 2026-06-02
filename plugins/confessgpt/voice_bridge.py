"""
ConfessGPT — voice bridge.

Thin wrapper around ``core.services.voice.VoiceService`` for the
confessor:

- TTS for every confessor utterance (Italian voice, low speed, solemn).
- STT for the penitent reply.
- Audio is never persisted to disk by this module. Bytes flow through
  the request/response only — the sigillum extends to voice.
"""

from __future__ import annotations

import asyncio
import base64

from core.observability.logging import get_logger
from core.services.voice import VoiceProvider, VoiceService

logger = get_logger(__name__)

# Hard ceiling on each TTS/STT call so a missing API key or slow
# provider cannot stall the rite. The plugin gracefully degrades to
# text-only when this fires. 12 s comfortably covers OpenAI TTS on a
# 2-3 sentence absolution formula; lower values clip valid replies.
_VOICE_TIMEOUT_SECONDS: float = 12.0


class VoiceBridge:
    """Bidirectional voice I/O for the confessor.

    The bridge is optional: if the underlying VoiceService is unable
    to reach a provider, calls degrade to ``None`` and the rite
    proceeds in text-only mode.
    """

    DEFAULT_VOICE_NAME = "onyx"  # deep male, fits a priest's voice
    DEFAULT_SPEED = 0.92  # slightly slower than natural — solemn

    def __init__(
        self,
        *,
        service: VoiceService,
        voice_name: str | None = None,
        voice_speed: float = DEFAULT_SPEED,
        provider: VoiceProvider | None = None,
    ) -> None:
        self._service = service
        self._voice_name = voice_name or self.DEFAULT_VOICE_NAME
        self._voice_speed = voice_speed
        self._provider = provider

    async def speak(self, text: str) -> tuple[str, str] | None:
        """Synthesize a confessor utterance.

        Returns ``(base64_audio, mime)`` or ``None`` on degraded mode.
        """
        if not text.strip():
            return None
        try:
            response = await asyncio.wait_for(
                self._service.text_to_speech(
                    text=text,
                    voice=self._voice_name,
                    speed=self._voice_speed,
                    provider=self._provider,
                ),
                timeout=_VOICE_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, TimeoutError):
            logger.warning("confessgpt_tts_timeout")
            return None
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            logger.warning("confessgpt_tts_unavailable", error=str(exc)[:200])
            return None
        return response.audio_base64, "audio/mp3"

    async def listen(self, audio_bytes: bytes) -> str:
        """Transcribe penitent audio. Returns empty string on failure."""
        if not audio_bytes:
            return ""
        try:
            response = await asyncio.wait_for(
                self._service.speech_to_text(
                    audio_data=audio_bytes,
                    language="it",
                    provider=self._provider,
                ),
                timeout=_VOICE_TIMEOUT_SECONDS * 1.5,
            )
        except (asyncio.TimeoutError, TimeoutError):
            logger.warning("confessgpt_stt_timeout")
            return ""
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            logger.warning("confessgpt_stt_unavailable", error=str(exc)[:200])
            return ""
        return response.text


def decode_b64_audio(b64: str) -> bytes:
    """Decode a base64-encoded audio payload uploaded by the client."""
    return base64.b64decode(b64.encode("ascii"))
