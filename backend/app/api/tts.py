import base64
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field, StringConstraints

from app.api.deps import SessionDep, TTSSynthesizeRateLimitDep
from app.application.museum_profile_service import get_museum_configuration, get_session_museum_configuration
from app.application.tour_session_service import verify_session_token
from app.application.tts_service import DEFAULT_TTS_VOICE
from app.domain.exceptions import TourSessionExpired, TourSessionNotFound, TourSessionTokenMismatch
from app.infra.providers.tts.base import (
    InvalidWAVAudioError,
    TTSConfig,
    require_valid_wav,
)

router = APIRouter(prefix="/tts", tags=["tts"])


class SynthesizeRequest(BaseModel):
    text: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
    ]
    # ``voice`` remains a compatibility field; the service currently uses the
    # centrally configured voice even when this value is empty or customized.
    voice: str | None = Field(default=DEFAULT_TTS_VOICE, max_length=64)
    style: str | None = Field(default=None, max_length=500)
    persona: Literal["default", "A", "B", "C", "D"] | None = None
    session_id: str | None = Field(default=None, min_length=1, max_length=64)


class SynthesizeResponse(BaseModel):
    audio: str  # base64-encoded WAV audio
    format: str = "wav"


def _get_tts_service(request: Request):
    return getattr(request.app.state, "tts_service", None)


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_tts(
    body: SynthesizeRequest,
    request: Request,
    session: SessionDep,
    _rate_limit: TTSSynthesizeRateLimitDep,
    x_session_token: str | None = Header(None),
):
    tts_service = _get_tts_service(request)
    if tts_service is None:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available. Check TTS_ENABLED and TTS_API_KEY in server config.",
        )

    if body.session_id:
        if not x_session_token:
            raise HTTPException(status_code=403, detail="Session token required")
        try:
            await verify_session_token(session, body.session_id, x_session_token)
            configuration = await get_session_museum_configuration(session, body.session_id)
        except TourSessionNotFound:
            raise HTTPException(status_code=404, detail="Tour session not found") from None
        except TourSessionTokenMismatch:
            raise HTTPException(status_code=403, detail="Invalid session token") from None
        except TourSessionExpired:
            raise HTTPException(status_code=410, detail="Tour session expired") from None
        await session.commit()
    else:
        configuration = await get_museum_configuration(session)
        await session.rollback()
    policy = configuration.museum.business.tts
    if body.persona:
        config = await tts_service.get_tour_tts_config(body.persona, policy=policy)
        if body.style:
            base_style = config.style or ""
            config.style = (base_style + "\n" + body.style).strip()
    else:
        config = TTSConfig(voice=policy.default_voice, style=policy.default_style)
        if body.style:
            config.style = ((config.style or "") + "\n" + body.style).strip()
    try:
        audio_bytes = require_valid_wav(await tts_service.provider.synthesize(body.text, config))
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    except Exception as exc:
        stage = "wav_validation" if isinstance(exc, InvalidWAVAudioError) else "provider"
        logger.warning(
            "TTS synthesis failed provider={} stage={} error_type={}",
            type(tts_service.provider).__name__,
            stage,
            type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="TTS synthesis failed") from None

    return SynthesizeResponse(
        audio=audio_b64,
        format="wav",
    )
