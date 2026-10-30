from app.application.ports.prompt_gateway import PromptGateway
from app.domain.tts_config import (
    DEFAULT_TTS_STYLE,
    DEFAULT_TTS_VOICE,
    MuseumTTSConfig,
)
from app.infra.providers.tts.base import BaseTTSProvider, TTSConfig

VOICE_DESCRIPTION_KEY = "__voice_description__"
VOICE_KEY = "__voice__"


def extract_voice_description(variables: list[dict[str, str]]) -> str | None:
    """Extract voice_description from the variables metadata list."""
    for var in variables:
        if var.get("name") == VOICE_DESCRIPTION_KEY:
            return var.get("description", "")
    return None


def extract_voice(variables: list[dict[str, str]]) -> str | None:
    """Extract preset voice name from the variables metadata list."""
    for var in variables:
        if var.get("name") == VOICE_KEY:
            return var.get("description", "")
    return None


def store_voice_description(variables: list[dict[str, str]], voice_description: str) -> list[dict[str, str]]:
    """Store voice_description in the variables metadata list."""
    cleaned = [v for v in variables if v.get("name") != VOICE_DESCRIPTION_KEY]
    if voice_description:
        cleaned.append({"name": VOICE_DESCRIPTION_KEY, "description": voice_description})
    return cleaned


class TTSService:
    def __init__(self, provider: BaseTTSProvider, prompt_gateway: PromptGateway):
        self.provider = provider
        self.prompt_gateway = prompt_gateway

    def get_qa_tts_config(self, user_voice: str | None = None, *, policy: MuseumTTSConfig | None = None) -> TTSConfig:
        # Voice parameters from old visitors cannot override the museum policy.
        policy = policy or MuseumTTSConfig()
        return TTSConfig(voice=policy.default_voice, style=policy.default_style)

    async def get_tour_tts_config(self, persona: str, *, policy: MuseumTTSConfig | None = None) -> TTSConfig:
        if policy is not None:
            choice = policy.personas.get(persona) or policy.personas.get("default")
            return TTSConfig(
                voice=(choice.voice if choice else "") or policy.default_voice,
                style=(choice.style if choice else "") or policy.default_style,
            )
        # Compatibility for integrations which have not adopted museum profiles.
        prompt = await self.prompt_gateway.get_entity(f"tour_tts_persona_{persona.lower()}")
        prompt_voice = extract_voice(prompt.variables) if prompt else None
        prompt_style = extract_voice_description(prompt.variables) if prompt else None
        return TTSConfig(
            voice=prompt_voice or DEFAULT_TTS_VOICE,
            style=prompt_style or DEFAULT_TTS_STYLE,
        )
