"""Validated route content owned by each museum."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

RouteText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
HallSlug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)]


class RouteProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    theme: RouteText
    summary: RouteText
    focus: RouteText
    questions: list[Annotated[str, StringConstraints(min_length=1, max_length=200)]] = Field(
        min_length=1, max_length=12
    )
    preferred_halls: list[HallSlug] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def unique_destinations(self) -> Self:
        if len(set(self.preferred_halls)) != len(self.preferred_halls):
            raise ValueError("Route preferred_halls must not repeat a destination")
        return self


class RouteDuration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_minutes: int = Field(ge=1, le=1440, strict=True)
    stops: int = Field(ge=1, le=100, strict=True)


_DEFAULT_ROUTE_PROFILES = {
    "A": {
        "theme": "考古研究路线",
        "summary": "围绕当前开放展厅中的器物、遗迹与历史材料，建立观察、证据与解释之间的联系。",
        "focus": "区分观察到的事实与推断，关注来源、年代和可验证的证据。",
        "questions": ["哪些细节可以作为历史证据？", "这些材料能支持哪些解释？"],
        "preferred_halls": ["basic-exhibition-hall", "site-protection-hall", "kiln-hall", "prehistoric-workshop"],
    },
    "B": {
        "theme": "研学记录路线",
        "summary": "把参观拆成观察任务、记录点和复盘线索，形成可整理、可汇报的研学笔记。",
        "focus": "记录展品名称、年代、用途与关键细节，整理需要继续查证的问题。",
        "questions": ["我应该先记录哪些信息？", "哪些问题适合继续查证？"],
        "preferred_halls": [
            "basic-exhibition-hall",
            "education-center",
            "prehistoric-workshop",
            "site-protection-hall",
        ],
    },
    "C": {
        "theme": "历史追问路线",
        "summary": "从当前展陈中的历史问题出发，追问社会生活、文化变化与今天的联系。",
        "focus": "结合可靠史料理解历史背景，区分事实、解释与想象。",
        "questions": ["这些展品反映了怎样的历史生活？", "还有哪些问题需要证据支持？"],
        "preferred_halls": [
            "site-protection-hall",
            "basic-exhibition-hall",
            "banpo-girl-sculpture",
            "education-center",
        ],
    },
    "D": {
        "theme": "器物观察路线",
        "summary": "优先观察当前器物展品的形制、材料、纹饰、工艺和使用痕迹，再联系其历史背景。",
        "focus": "比较器物的形制、材料、工艺与使用痕迹，以现场展陈为依据。",
        "questions": ["这件器物有哪些值得观察的细节？", "材料和工艺能说明什么？"],
        "preferred_halls": ["basic-exhibition-hall", "kiln-hall", "prehistoric-workshop", "site-protection-hall"],
    },
    "default": {
        "theme": "AI 默认参观路线",
        "summary": "根据当前开放展厅和参观时间，先建立整体印象，再逐步观察展品和历史线索。",
        "focus": "先了解展厅主题，再选择感兴趣的展品观察和提问。",
        "questions": ["这个展厅有哪些看点？", "这些展品说明了怎样的历史？"],
        "preferred_halls": ["basic-exhibition-hall", "site-protection-hall", "kiln-hall", "prehistoric-workshop"],
    },
}


def default_route_profiles() -> dict[str, RouteProfile]:
    return {code: RouteProfile.model_validate(value) for code, value in _DEFAULT_ROUTE_PROFILES.items()}


def default_route_durations() -> list[RouteDuration]:
    return [
        RouteDuration(max_minutes=minutes, stops=stops) for minutes, stops in [(35, 2), (75, 3), (120, 4), (1440, 5)]
    ]
