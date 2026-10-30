"""Portable museum voice choices; provider credentials remain deployment settings."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_TTS_VOICE = "冰糖"
DEFAULT_TTS_STYLE = (
    "只朗读给定文本，不要补充任何内容。"
    "固定使用“冰糖”美少女声线，声音清甜、明亮、自然、年轻。"
    "不要使用男声、低沉声线或中年感声线。"
    "语速正常偏快，句间停顿短，尾音不要拖长。"
)


class TTSVoiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    voice: str = Field(default="", max_length=64)
    style: str = Field(default="", max_length=2000)


class MuseumTTSConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    default_voice: str = Field(default=DEFAULT_TTS_VOICE, min_length=1, max_length=64)
    default_style: str = Field(default=DEFAULT_TTS_STYLE, max_length=2000)
    personas: dict[Literal["A", "B", "C", "D", "default"], TTSVoiceConfig] = Field(default_factory=dict, max_length=5)
