# backend/app/application/curator_service.py
import re
from typing import TYPE_CHECKING, Any

from app.application.hall_normalizer import normalize_hall
from app.application.ports.repositories import CuratorAgentPort
from app.domain.exceptions import EntityNotFoundError
from app.domain.route_config import RouteDuration, default_route_durations, default_route_profiles

if TYPE_CHECKING:
    from app.domain.business_config import MuseumBusinessConfig

from .exhibit_service import ExhibitService
from .profile_service import ProfileService

_PERSONA_IDS = {"A", "B", "C", "D", "default"}


def _normalize_persona(interests: list[str] | None) -> str:
    if not interests:
        return "default"

    for raw in interests:
        text = str(raw or "").strip()
        if not text:
            continue
        match = re.search(
            r"(?:persona|personaId)\s*[:=]\s*(default|[A-Da-d])\b",
            text,
        )
        if match:
            token = match.group(1)
            normalized = token if token == "default" else token.upper()
            return normalized if normalized in _PERSONA_IDS else "default"

    joined = " ".join(str(item) for item in interests)
    for code in ("A", "B", "C", "D"):
        if f"persona:{code}" in joined or f"personaId:{code}" in joined:
            return code
    return "default"


def _step_count_for_time(available_time: int, durations: list[RouteDuration] | None = None) -> int:
    thresholds = durations if durations is not None else default_route_durations()
    for threshold in thresholds:
        if available_time <= threshold.max_minutes:
            return threshold.stops
    return thresholds[-1].stops


def _allocate_minutes(total_minutes: int, count: int) -> list[int]:
    count = max(1, count)
    base = max(1, total_minutes // count)
    minutes = [base for _ in range(count)]
    remainder = max(0, total_minutes - base * count)
    for idx in range(remainder):
        minutes[idx % count] += 1
    return minutes


def format_route_plan_text(route: dict[str, Any]) -> str:
    lines = [route["summary"]]
    for step in route["steps"]:
        lines.append(f"{step['order']}. {step['hall_name']}：{step['title']}。{step['focus']}")
    return "\n".join(lines)


def _route_plan_text(route: dict[str, Any]) -> str:
    return format_route_plan_text(route)


def build_structured_route(
    available_time: int,
    interests: list[str] | None = None,
    *,
    halls: list[dict[str, Any]] | None = None,
    business: "MuseumBusinessConfig | None" = None,
) -> dict[str, Any]:
    """Build a bounded itinerary exclusively from the supplied active catalog."""
    persona = _normalize_persona(interests)
    profiles = business.routes if business is not None else default_route_profiles()
    profile = profiles.get(persona, profiles["default"])
    catalog: dict[str, dict[str, Any]] = {}
    for hall in halls or []:
        slug = normalize_hall(hall.get("slug"))
        name = str(hall.get("name") or "").strip()
        if slug and slug == hall.get("slug") and name and hall.get("is_active") is True:
            catalog.setdefault(slug, hall)

    ordered_slugs = [slug for slug in profile.preferred_halls if slug in catalog]
    ordered_slugs.extend(slug for slug in catalog if slug not in ordered_slugs)
    selected_slugs = ordered_slugs[
        : min(
            max(1, available_time),
            _step_count_for_time(available_time, business.route_durations if business is not None else None),
        )
    ]
    minutes = _allocate_minutes(max(available_time, 1), len(selected_slugs))

    steps: list[dict[str, Any]] = []
    for idx, slug in enumerate(selected_slugs):
        hall = catalog[slug]
        name = str(hall["name"]).strip()
        description = str(hall.get("description") or "").strip()
        questions = [str(question).strip() for question in hall.get("suggested_questions", []) if str(question).strip()]
        steps.append(
            {
                "order": idx + 1,
                "hall_slug": slug,
                "hall_name": name,
                "title": f"参观{name}",
                "reason": description or f"结合{name}的当前展陈，按目录安排参观。",
                "focus": str(profile.focus),
                "estimated_minutes": minutes[idx],
                "suggested_questions": questions or list(profile.questions),
            }
        )

    return {
        "source": "curator",
        "total_minutes": available_time,
        "theme": profile.theme,
        "summary": profile.summary if steps else "当前暂无开放展厅，暂时无法生成参观路线。",
        "steps": steps,
    }


class CuratorService:
    """策展人协调服务，整合展品、画像和策展智能体提供导览服务。"""

    def __init__(
        self,
        curator_agent: CuratorAgentPort,
        profile_service: ProfileService,
        exhibit_service: ExhibitService,
    ):
        self._curator_agent = curator_agent
        self._profile_service = profile_service
        self._exhibit_service = exhibit_service

    async def plan_tour(
        self,
        user_id: str,
        available_time: int,
        interests: list[str] | None = None,
        *,
        halls: list[dict[str, Any]] | None = None,
        business: "MuseumBusinessConfig | None" = None,
    ) -> dict[str, Any]:
        """规划参观路线。

        Args:
            user_id: 用户ID
            available_time: 可用时间（分钟）
            interests: 兴趣标签列表（可选，默认使用用户画像中的兴趣）

        Returns:
            包含路线规划结果的字典
        """
        is_guest = user_id.startswith("guest-")
        if is_guest:
            tour_interests = interests or []
            visited_ids: list[str] = []
        else:
            # 获取或创建用户画像
            profile = await self._profile_service.get_or_create_profile(user_id)

            # 使用用户兴趣或传入的兴趣
            tour_interests = interests if interests is not None else profile.interests
            visited_ids = [eid.value for eid in profile.visited_exhibit_ids]

        route = build_structured_route(available_time, tour_interests, halls=halls, business=business)

        # 构建规划请求
        plan_request = f"""请为我规划一条博物馆参观路线。

可用时间：{available_time}分钟
兴趣标签：{", ".join(tour_interests) if tour_interests else "无特定偏好"}
已参观展品：{", ".join(visited_ids) if visited_ids else "无"}

已核验的当前开放展厅路线：
{_route_plan_text(route)}

请使用path_planning工具补充参观建议，仅使用上述开放展厅，不得引入其他目的地。"""

        if is_guest or not route["steps"]:
            result = {"output": _route_plan_text(route), "session_id": ""}
        else:
            # 调用策展智能体；结构化 route 已由规则生成，智能体失败也不影响接口可用。
            try:
                result = await self._curator_agent.run(
                    user_input=plan_request,
                    chat_history=[],
                )
            except Exception:
                result = {"output": _route_plan_text(route), "session_id": ""}

        return {
            "user_id": user_id,
            "available_time": available_time,
            "interests": tour_interests,
            "visited_exhibit_ids": visited_ids,
            # Free-form agent output cannot authorize additional destinations.
            "plan": _route_plan_text(route),
            "route": route,
            "session_id": result.get("session_id", ""),
        }

    async def generate_narrative(
        self,
        user_id: str,
        exhibit_id: str,
    ) -> dict[str, Any]:
        """为展品生成叙事内容。

        Args:
            user_id: 用户ID
            exhibit_id: 展品ID

        Returns:
            包含叙事内容的字典

        Raises:
            EntityNotFoundError: 如果展品不存在
        """
        # 获取展品信息
        exhibit = await self._exhibit_service.get_exhibit(exhibit_id)
        if exhibit is None:
            raise EntityNotFoundError(f"Exhibit not found: {exhibit_id}")

        # 获取用户画像
        profile = await self._profile_service.get_or_create_profile(user_id)

        # 构建叙事生成请求
        narrative_request = f"""请为以下展品生成讲解内容：

展品名称：{exhibit.name}
展品描述：{exhibit.description}
展品年代：{exhibit.era}
展品类别：{exhibit.category}

用户知识水平：{profile.knowledge_level}
用户叙事偏好：{profile.narrative_preference}

请使用narrative_generation工具生成叙事内容。"""

        # 调用策展智能体
        result = await self._curator_agent.run(
            user_input=narrative_request,
            chat_history=[],
        )

        # 记录参观
        await self._profile_service.record_visit(user_id, exhibit_id)

        return {
            "user_id": user_id,
            "exhibit_id": exhibit_id,
            "exhibit_name": exhibit.name,
            "narrative": result.get("output", ""),
            "knowledge_level": profile.knowledge_level,
            "narrative_preference": profile.narrative_preference,
            "session_id": result.get("session_id", ""),
        }

    async def get_reflection_prompts(
        self,
        user_id: str,
        exhibit_id: str,
    ) -> dict[str, Any]:
        """获取展品的反思提示问题。

        Args:
            user_id: 用户ID
            exhibit_id: 展品ID

        Returns:
            包含反思提示的字典

        Raises:
            EntityNotFoundError: 如果展品不存在
        """
        # 获取展品信息
        exhibit = await self._exhibit_service.get_exhibit(exhibit_id)
        if exhibit is None:
            raise EntityNotFoundError(f"Exhibit not found: {exhibit_id}")

        # 获取用户画像
        profile = await self._profile_service.get_or_create_profile(user_id)

        # 构建反思提示请求
        reflection_request = f"""请为以下展品生成反思提示问题：

展品名称：{exhibit.name}
展品类别：{exhibit.category}

用户知识水平：{profile.knowledge_level}
反思深度：{profile.reflection_depth}

请使用reflection_prompts工具生成反思问题。"""

        # 调用策展智能体
        result = await self._curator_agent.run(
            user_input=reflection_request,
            chat_history=[],
        )

        return {
            "user_id": user_id,
            "exhibit_id": exhibit_id,
            "exhibit_name": exhibit.name,
            "reflection_prompts": result.get("output", ""),
            "knowledge_level": profile.knowledge_level,
            "reflection_depth": profile.reflection_depth,
            "session_id": result.get("session_id", ""),
        }

    async def chat(
        self,
        user_id: str,
        message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """与策展人进行对话。

        Args:
            user_id: 用户ID
            message: 用户消息
            chat_history: 聊天历史（可选）

        Returns:
            包含回复内容的字典
        """
        # 获取用户画像以提供上下文
        profile = await self._profile_service.get_or_create_profile(user_id)

        # 构建系统上下文
        context = f"""当前用户信息：
- 知识水平：{profile.knowledge_level}
- 叙事偏好：{profile.narrative_preference}
- 兴趣标签：{", ".join(profile.interests) if profile.interests else "无"}
- 已参观展品数：{len(profile.visited_exhibit_ids)}

用户问题：{message}"""

        # 调用策展智能体
        result = await self._curator_agent.run(
            user_input=context,
            chat_history=chat_history or [],
        )

        return {
            "user_id": user_id,
            "message": message,
            "response": result.get("output", ""),
            "session_id": result.get("session_id", ""),
            "error": result.get("error"),
        }

    async def get_exhibit_info(
        self,
        user_id: str,
        exhibit_id: str,
    ) -> dict[str, Any]:
        """获取展品详细信息（包含知识检索）。

        Args:
            user_id: 用户ID
            exhibit_id: 展品ID

        Returns:
            包含展品信息和相关知识的字典

        Raises:
            EntityNotFoundError: 如果展品不存在
        """
        # 获取展品信息
        exhibit = await self._exhibit_service.get_exhibit(exhibit_id)
        if exhibit is None:
            raise EntityNotFoundError(f"Exhibit not found: {exhibit_id}")

        # 获取用户画像
        await self._profile_service.get_or_create_profile(user_id)

        # 构建知识检索请求
        knowledge_request = f"""请检索以下展品的相关知识：

展品名称：{exhibit.name}
展品描述：{exhibit.description}
展品年代：{exhibit.era}
展品类别：{exhibit.category}

请使用knowledge_retrieval工具检索相关知识，exhibit_id为"{exhibit_id}"。"""

        # 调用策展智能体
        result = await self._curator_agent.run(
            user_input=knowledge_request,
            chat_history=[],
        )

        return {
            "user_id": user_id,
            "exhibit_id": exhibit_id,
            "exhibit": {
                "id": exhibit.id.value,
                "name": exhibit.name,
                "description": exhibit.description,
                "category": exhibit.category,
                "era": exhibit.era,
                "hall": exhibit.hall,
                "importance": exhibit.importance,
                "estimated_visit_time": exhibit.estimated_visit_time,
            },
            "knowledge": result.get("output", ""),
            "session_id": result.get("session_id", ""),
        }
