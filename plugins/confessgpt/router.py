"""
ConfessGPT — FastAPI router.

Exposes three endpoints under the plugin prefix (default ``/api/confessgpt``):

- ``POST /sessions`` — open a fresh confession session.
- ``POST /turn`` — advance the rite by one turn (text in, text+optional
  audio out).
- ``POST /voice/turn`` — same as ``/turn`` but the penitent provides a
  base64-encoded audio blob instead of text.

The router is intentionally thin: all sacramental logic lives in
``flow.py``. The router never logs penitent content; only phases and
session ids appear in observability output.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from core.observability.logging import get_logger

from .flow import (
    ConfessionFlow,
    SessionAlreadyClosed,
    SessionNotFound,
)
from .models import (
    RitePhase,
    SessionCreateRequest,
    SessionCreateResponse,
    TurnRequest,
    TurnResponse,
)
from .sigillum import SigillumStore
from .voice_bridge import decode_b64_audio

logger = get_logger(__name__)


class VoiceTurnRequest(TurnRequest):
    """Penitent turn with audio payload (base64-encoded)."""

    audio_base64: str = ""


def create_router(plugin_instance: Any) -> APIRouter:
    """Construct the confessor router bound to a live plugin instance."""

    router = APIRouter(prefix="", tags=["ConfessGPT"])

    @router.get("/info")
    async def info() -> dict[str, Any]:
        return {
            "plugin": plugin_instance.metadata.name,
            "version": plugin_instance.metadata.version,
            "voice_enabled": plugin_instance.voice_bridge is not None,
            "model_id": plugin_instance.model_id,
            "rite": "roman_post_vatican_ii_it_cei",
        }

    @router.post("/sessions", response_model=SessionCreateResponse)
    async def open_session(
        req: SessionCreateRequest,
    ) -> SessionCreateResponse:
        del req  # voice toggle is a hint; the server decides per-turn
        try:
            store = _store(plugin_instance)
            state = await store.create()
            return SessionCreateResponse(session_id=state.session_id)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 — never bare-500 the rite
            logger.exception("confessgpt_session_open_failed", error=str(exc)[:200])
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Apertura sessione fallita: {exc}",
            ) from exc

    @router.post("/turn", response_model=TurnResponse)
    async def turn(req: TurnRequest) -> TurnResponse:
        return await _execute_turn(
            plugin_instance,
            session_id=req.session_id,
            penitent_utterance=req.utterance,
            tts=True,
        )

    @router.post("/voice/turn", response_model=TurnResponse)
    async def voice_turn(req: VoiceTurnRequest) -> TurnResponse:
        bridge = plugin_instance.voice_bridge
        utterance = req.utterance
        if req.audio_base64 and bridge is not None:
            try:
                audio_bytes = decode_b64_audio(req.audio_base64)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"audio_base64 non decodificabile: {exc}",
                ) from exc
            transcribed = await bridge.listen(audio_bytes)
            utterance = transcribed or utterance
        return await _execute_turn(
            plugin_instance,
            session_id=req.session_id,
            penitent_utterance=utterance,
            tts=True,
        )

    @router.delete("/sessions/{session_id}")
    async def close_session(session_id: str) -> dict[str, Any]:
        store = _store(plugin_instance)
        if store.is_closed(session_id):
            return {"session_id": session_id, "closed": True}
        await store.close(session_id)
        return {"session_id": session_id, "closed": True}

    return router


async def _execute_turn(
    plugin_instance: Any,
    *,
    session_id: str,
    penitent_utterance: str,
    tts: bool,
) -> TurnResponse:
    flow: ConfessionFlow | None = plugin_instance.flow
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin non inizializzato.",
        )
    try:
        turn_obj, state, closed = await flow.step(
            session_id=session_id,
            penitent_utterance=penitent_utterance,
        )
    except SessionNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessione non trovata o già chiusa (sigillum).",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — keep the rite alive
        # Anything else (LLM transport, voice glitch, observability hook,
        # tenant context, ...) must NOT 500 the rite. Return a
        # canonical pastoral nudge so the penitent can keep going.
        if isinstance(exc, SessionAlreadyClosed):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Sessione conclusa: il sigillo sacramentale è stato sigillato.",
            ) from exc
        logger.exception("confessgpt_turn_unhandled_error", error=str(exc)[:200])
        return TurnResponse(
            session_id=session_id,
            phase=RitePhase.ACCOGLIENZA,
            utterance=("Prendi il tempo che ti serve. Quando sei pronto, parla."),
            next_phase=RitePhase.ACCOGLIENZA,
            advance_on_user_reply=True,
            closed=False,
            audio_base64=None,
            audio_mime=None,
        )

    audio_b64: str | None = None
    audio_mime: str | None = None
    bridge = plugin_instance.voice_bridge
    if tts and bridge is not None:
        spoken = await bridge.speak(turn_obj.utterance)
        if spoken is not None:
            audio_b64, audio_mime = spoken

    return TurnResponse(
        session_id=state.session_id,
        phase=turn_obj.phase,
        utterance=turn_obj.utterance,
        next_phase=turn_obj.next_phase,
        advance_on_user_reply=turn_obj.advance_on_user_reply,
        closed=closed,
        audio_base64=audio_b64,
        audio_mime=audio_mime,
    )


def _store(plugin_instance: Any) -> SigillumStore:
    store: SigillumStore | None = plugin_instance.store
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin non inizializzato.",
        )
    return store
