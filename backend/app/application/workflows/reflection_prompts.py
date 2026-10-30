from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING

from app.domain.reflection_config import (
    BEGINNER_PROMPTS,
    CATEGORY_REFLECTIONS,
    EXPERT_PROMPTS,
    INTERMEDIATE_PROMPTS,
    STYLE_DEFAULTS,
)

if TYPE_CHECKING:
    from app.domain.business_config import MuseumBusinessConfig

from app.application.ports.prompt_gateway import PromptGateway


class KnowledgeLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class NarrativeStyle(Enum):
    STORYTELLING = "storytelling"
    ACADEMIC = "academic"
    INTERACTIVE = "interactive"


NARRATIVE_STYLE_PROMPTS = {NarrativeStyle(key): value for key, value in STYLE_DEFAULTS.items()}

REFLECTION_TEMPLATES = {
    KnowledgeLevel.BEGINNER: BEGINNER_PROMPTS,
    KnowledgeLevel.INTERMEDIATE: INTERMEDIATE_PROMPTS,
    KnowledgeLevel.EXPERT: EXPERT_PROMPTS,
}

LEVEL_KEY_MAP = {
    KnowledgeLevel.BEGINNER: "reflection_beginner",
    KnowledgeLevel.INTERMEDIATE: "reflection_intermediate",
    KnowledgeLevel.EXPERT: "reflection_expert",
}

CATEGORY_KEY_MAP = {
    "青铜器": "reflection_bronze",
    "书画": "reflection_painting",
    "陶瓷": "reflection_ceramic",
}

STYLE_KEY_MAP = {
    NarrativeStyle.STORYTELLING: "narrative_style_storytelling",
    NarrativeStyle.ACADEMIC: "narrative_style_academic",
    NarrativeStyle.INTERACTIVE: "narrative_style_interactive",
}


def _parse_multiline_prompts(content: str) -> list[str]:
    prompts = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if line:
            prompts.append(line)
    return prompts


class ReflectionPromptService:
    def __init__(
        self,
        prompt_gateway: PromptGateway | None = None,
        config_loader: Callable[[], Awaitable["MuseumBusinessConfig"]] | None = None,
    ):
        self._prompt_gateway = prompt_gateway
        self._config_loader = config_loader

    async def _get_prompt_content(self, key: str) -> str | None:
        if self._prompt_gateway:
            return await self._prompt_gateway.get(key)
        return None

    async def get_reflection_prompts(
        self,
        knowledge_level: KnowledgeLevel,
        reflection_depth: int = 3,
        category: str | None = None,
        business_config: "MuseumBusinessConfig | None" = None,
    ) -> list[str]:
        if reflection_depth < 1:
            raise ValueError("reflection_depth must be at least 1")
        if reflection_depth > 5:
            raise ValueError("reflection_depth cannot exceed 5")

        configuration = business_config
        if configuration is None and self._config_loader is not None:
            configuration = await self._config_loader()
        if configuration is not None:
            return get_reflection_prompts_sync(knowledge_level, reflection_depth, category, configuration)

        prompts: list[str] = []

        if category:
            category_key = CATEGORY_KEY_MAP.get(category)
            if category_key:
                content = await self._get_prompt_content(category_key)
                if content:
                    prompts.extend(_parse_multiline_prompts(content))
                else:
                    prompts.extend(CATEGORY_REFLECTIONS.get(category, []))
            else:
                prompts.extend(CATEGORY_REFLECTIONS.get(category, []))

        level_key = LEVEL_KEY_MAP.get(knowledge_level)
        if level_key:
            content = await self._get_prompt_content(level_key)
            if content:
                prompts.extend(_parse_multiline_prompts(content))
            else:
                prompts.extend(REFLECTION_TEMPLATES.get(knowledge_level, BEGINNER_PROMPTS))
        else:
            prompts.extend(REFLECTION_TEMPLATES.get(knowledge_level, BEGINNER_PROMPTS))

        return prompts[:reflection_depth]

    async def get_narrative_style_prompt(
        self,
        style: NarrativeStyle,
        business_config: "MuseumBusinessConfig | None" = None,
    ) -> str:
        if not isinstance(style, NarrativeStyle):
            raise ValueError(f"Invalid narrative style: {style}")

        configuration = business_config
        if configuration is None and self._config_loader is not None:
            configuration = await self._config_loader()
        if configuration is not None:
            return configuration.reflection.narrative_styles[style.value]

        style_key = STYLE_KEY_MAP.get(style)
        if style_key:
            content = await self._get_prompt_content(style_key)
            if content:
                return content

        return NARRATIVE_STYLE_PROMPTS.get(style, NARRATIVE_STYLE_PROMPTS[NarrativeStyle.STORYTELLING])


def get_reflection_prompts_sync(
    knowledge_level: KnowledgeLevel,
    reflection_depth: int = 3,
    category: str | None = None,
    business_config: "MuseumBusinessConfig | None" = None,
) -> list[str]:
    if reflection_depth < 1:
        raise ValueError("reflection_depth must be at least 1")
    if reflection_depth > 5:
        raise ValueError("reflection_depth cannot exceed 5")

    if business_config is not None:
        prompts = []
        for item in business_config.categories:
            if category and category in {item.value, item.label}:
                prompts.extend(item.reflection_prompts)
                break
        level = knowledge_level.value if isinstance(knowledge_level, KnowledgeLevel) else "beginner"
        prompts.extend(business_config.reflection.level_prompts[level])
        return prompts[:reflection_depth]

    prompts: list[str] = []

    if category and category in CATEGORY_REFLECTIONS:
        prompts.extend(CATEGORY_REFLECTIONS[category])

    level_prompts = REFLECTION_TEMPLATES.get(knowledge_level, BEGINNER_PROMPTS)
    prompts.extend(level_prompts)

    return prompts[:reflection_depth]
