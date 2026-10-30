"""Portable business content; infrastructure and trusted-data rules stay in code."""

from typing import Annotated, Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.reflection_config import CATEGORY_REFLECTIONS, ReflectionConfig
from app.domain.route_config import RouteDuration, RouteProfile, default_route_durations, default_route_profiles
from app.domain.suggestion_config import SuggestionConfig
from app.domain.tts_config import MuseumTTSConfig
from app.domain.visitor_experience import VisitorExperience

Code = Literal["A", "B", "C", "D"]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Key = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]*$", max_length=64)]


class BusinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FocusOption(BusinessModel):
    code: Code
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    description: str = Field(default="", max_length=1000)
    context: str = Field(default="", max_length=2000)


class AssumptionOption(FocusOption):
    topic: Key
    chat_context: Text
    challenge: str = Field(default="", max_length=2000)
    review_hint: Text


def default_focus_options() -> list[FocusOption]:
    return [
        FocusOption(code=cast(Code, code), label=label, description=desc, context=desc)
        for code, label, desc in [
            ("A", "带着任务研学", "边看边记，把展厅整理成可复盘的笔记"),
            ("B", "证据怎样成史", "像研究者一样，看证据、推理和不确定性"),
            ("C", "历史问题追问", "联系历史背景和今天的生活来理解"),
            ("D", "器物细节观察", "从材料、器形、纹饰和工艺读懂文物"),
        ]
    ]


def default_assumption_options() -> list[AssumptionOption]:
    # These meanings match the three-step questionnaire shipped before C.
    return [
        AssumptionOption(
            code=cast(Code, code),
            label=label,
            description=desc,
            topic=topic,
            chat_context=f"游客选择从{label}线索了解历史：{desc}。这是一种关注方向，不代表已得出结论。",
            challenge=f"结合{label}线索核对现场材料，不把兴趣选择解释成既定历史判断。",
            review_hint=f"最初希望从{label}线索了解历史：{desc}。",
        )
        for code, label, desc, topic in [
            ("A", "工艺", "陶器、石器和骨器如何被制作出来", "craft"),
            ("B", "聚落", "房屋、壕沟、墓葬如何组织空间", "settlement"),
            ("C", "社会组织", "分工、协作、规则和公共生活如何形成", "social"),
            ("D", "精神文化", "图案、仪式和形象如何表达观念", "spiritual"),
        ]
    ]


class QuestionnaireConfig(BusinessModel):
    focus_title: Text = "今天你最希望从哪个角度参观{museum_name}？"
    persona_title: Text = "接下来希望 MuseAI 以哪种身份陪你？"
    assumption_title: Text = "凭直觉，你最想从哪种线索了解这里的历史？"
    focus_options: list[FocusOption] = Field(default_factory=default_focus_options, min_length=4, max_length=4)
    assumption_options: list[AssumptionOption] = Field(
        default_factory=default_assumption_options, min_length=4, max_length=4
    )

    @model_validator(mode="after")
    def stable_codes(self) -> Self:
        for options in (self.focus_options, self.assumption_options):
            if {item.code for item in options} != set("ABCD"):
                raise ValueError("Each question requires one option for each stable code A, B, C, D")
        return self


class ExhibitCategory(BusinessModel):
    value: Key
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    reflection_prompts: list[Text] = Field(default_factory=list, max_length=20)


def default_categories() -> list[ExhibitCategory]:
    return [
        ExhibitCategory(
            value=value,
            label=label,
            reflection_prompts=list(CATEGORY_REFLECTIONS["陶瓷"]) if value in {"pottery", "painted_pottery"} else [],
        )
        for value, label in [
            ("painted_pottery", "彩陶与纹饰"),
            ("pottery", "陶器"),
            ("stone_tool", "石器工具"),
            ("bone_tool", "骨器"),
            ("settlement", "聚落遗址"),
            ("burial", "墓葬与体质人类学"),
            ("production", "生产与工艺"),
            ("symbol", "符号与精神文化"),
            ("education", "研学体验"),
            ("temporary", "临展内容"),
        ]
    ]


class RhythmOption(BusinessModel):
    value: Key
    label: Text


class DialogueConfig(BusinessModel):
    default_persona_prompt: Text = (
        "你是一位可信、友好且克制的博物馆导览员。游客选择了快速开始，未选择专门身份。"
        "围绕当前展厅、展品和用户问题解释，以现场观察和馆方资料为依据。"
    )
    persona_challenges: dict[str, Text] = Field(
        default_factory=lambda: {
            "default": "围绕眼前可观察的线索解释，在证据不足时说明不确定性。",
            "A": "区分直接看到的证据和推断，保留不确定性。",
            "B": "把观察转化为可以记录、核对的证据点。",
            "C": "连接具体材料与历史问题，说明解释需要的依据。",
            "D": "从材料、工艺和使用痕迹解释对象，区分事实和推测。",
        }
    )


class MuseumBusinessConfig(BusinessModel):
    version: Literal[1] = 1
    questionnaire: QuestionnaireConfig = Field(default_factory=QuestionnaireConfig)
    categories: list[ExhibitCategory] = Field(default_factory=default_categories, min_length=1, max_length=100)
    routes: dict[str, RouteProfile] = Field(default_factory=default_route_profiles)
    route_durations: list[RouteDuration] = Field(default_factory=default_route_durations, min_length=1, max_length=20)
    rhythms: list[RhythmOption] = Field(
        default_factory=lambda: [
            RhythmOption(value="notebook", label="研学记录模式"),
            RhythmOption(value="quick", label="30 分钟抓重点"),
            RhythmOption(value="dialogue", label="1 小时边看边问"),
            RhythmOption(value="research", label="研究深化模式"),
        ],
        min_length=1,
        max_length=20,
    )
    dialogue: DialogueConfig = Field(default_factory=DialogueConfig)
    reflection: ReflectionConfig = Field(default_factory=ReflectionConfig)
    suggestions: SuggestionConfig = Field(default_factory=SuggestionConfig)
    tts: MuseumTTSConfig = Field(default_factory=MuseumTTSConfig)
    visitor_experience: VisitorExperience | None = None

    @model_validator(mode="after")
    def consistent_references(self) -> Self:
        required = {"default", "A", "B", "C", "D"}
        if set(self.routes) != required or set(self.dialogue.persona_challenges) != required:
            raise ValueError("Routes and persona challenges require default, A, B, C, D")
        for values in ([item.value for item in self.categories], [item.value for item in self.rhythms]):
            if len(set(values)) != len(values):
                raise ValueError("Category and rhythm identifiers must be unique")
        durations = [item.max_minutes for item in self.route_durations]
        if durations != sorted(set(durations)):
            raise ValueError("Route time boundaries must be unique and increasing")
        for option in self.questionnaire.assumption_options:
            if option.topic not in self.reflection.topics:
                raise ValueError(f"Questionnaire topic does not exist: {option.topic}")
        return self


def public_business_configuration(business: MuseumBusinessConfig) -> dict[str, Any]:
    """Whitelist presentation fields; server prompts and scoring rules stay private."""
    data = business.model_dump(mode="json")
    questionnaire = data["questionnaire"]
    return {
        "version": business.version,
        "questionnaire": {
            **{key: questionnaire[key] for key in ("focus_title", "persona_title", "assumption_title")},
            "focus_options": [
                {key: item[key] for key in ("code", "label", "description")} for item in questionnaire["focus_options"]
            ],
            "assumption_options": [
                {key: item[key] for key in ("code", "label", "description", "topic")}
                for item in questionnaire["assumption_options"]
            ],
        },
        "categories": [{key: item[key] for key in ("value", "label")} for item in data["categories"]],
        "routes": data["routes"],
        "route_durations": data["route_durations"],
        "rhythms": data["rhythms"],
        "reflection": {
            "topics": {key: {"label": item.label} for key, item in business.reflection.topics.items()},
            "radar_dimensions": {
                key: {"label": item.label} for key, item in business.reflection.radar_dimensions.items()
            },
        },
        "tts": {
            "default_voice": business.tts.default_voice,
            "personas": {key: {"voice": item.voice} for key, item in business.tts.personas.items()},
        },
        "visitor_experience": data["visitor_experience"],
    }
