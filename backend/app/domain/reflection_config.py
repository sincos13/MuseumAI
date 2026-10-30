"""Validated museum-owned reflection and report rules, independent of runtime services."""

from string import Formatter
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

CERAMIC_KEYWORDS = [
    "陶",
    "瓷",
    "盆",
    "罐",
    "瓶",
    "碗",
    "鼎",
    "甑",
    "釜",
    "纹",
    "彩陶",
    "人面鱼纹",
    "鱼纹",
    "几何纹",
    "绳纹",
    "尖底瓶",
    "红陶",
    "灰陶",
    "黑陶",
    "泥塑",
    "陶塑",
    "陶器",
    "瓷器",
    "素面",
    "刻划",
    "彩绘",
]

OBSERVATION_TAGS = ["现场观察者", "展品探索者", "沉浸参观者"]

QUESTION_TAGS = ["好奇提问者", "展厅漫游者", "深度追问者"]

REVIEW_TAGS = ["参观记录者", "专注记录者", "细节发现者"]

REFLECTION_TOPIC_LABELS = {
    "craft": "器物工艺",
    "settlement": "聚落空间",
    "social": "社会组织",
    "spiritual": "精神文化",
    "life": "日常生活",
    "evidence": "证据推理",
}

PERSONA_REVIEW_ENTRY = {
    "default": ("evidence", "本次复盘按你的真实参观记录整理：先保留现场看到的内容和问过的问题，再归纳可以确认的线索。"),
    "A": ("evidence", "本次复盘先按证据链整理：实物、展签和遗迹位置优先于现成结论。"),
    "B": ("evidence", "本次复盘先按研学笔记整理：保留可回看、可继续追问的现场线索。"),
    "C": ("social", "本次复盘先按历史问题整理：从实际问题和回答中核对变化与联系。"),
    "D": ("craft", "本次复盘先按器物细节整理：材料、器形、纹饰和使用痕迹是主要入口。"),
}

REVIEW_TOPIC_LINES = {
    "craft": {
        "focus": "你的实际问题多次涉及展品如何制作、使用，以及哪些细节可以直接观察。",
        "evidence": "可回看{halls}中与这些问题直接相关的展品和展签，并对照本次问答记录。",
        "next": "继续区分哪些判断来自现场可见信息，哪些仍需要更多证据。",
    },
    "settlement": {
        "focus": "你的实际问题多次涉及展示对象之间的位置和空间关系。",
        "evidence": "可回看{halls}中与问题直接相关的位置说明，并对照本次问答记录。",
        "next": "继续核对空间判断来自哪些现场信息，避免把可能性写成确定结论。",
    },
    "social": {
        "focus": "你的实际问题多次涉及群体关系、协作或规则如何得到说明。",
        "evidence": "可回看{halls}中与这些问题直接相关的说明，比较问答中的依据是否相互支持。",
        "next": "继续追问每个判断需要哪些证据，并保留尚不能确认的部分。",
    },
    "spiritual": {
        "focus": "你的实际问题多次涉及图案、象征或观念应当如何理解。",
        "evidence": "可回看{halls}中问题所指的具体展示信息，并对照本次问答记录。",
        "next": "继续区分直接可见的形式与解释性的判断，避免超出已有信息。",
    },
    "life": {
        "focus": "你的实际问题多次涉及日常生活如何从现场信息得到说明。",
        "evidence": "可回看{halls}中问题所指的展品或说明，并对照本次问答记录。",
        "next": "继续从已确认的信息出发补充细节，不把未出现的内容加入结论。",
    },
    "evidence": {
        "focus": "关注点集中在证据推理：重要的不是记住结论，而是区分直接可见的材料和合理推断。",
        "evidence": "可回看{halls}中的展品、展签和遗迹位置，检查每个判断的证据来源。",
        "next": "继续追问一个判断背后需要哪些证据，并标出仍不确定的部分。",
    },
}

INSUFFICIENT_REVIEW_LINES = {
    "focus": "本次记录已经形成复盘起点：先保留现场观察，不急于把可能性写成结论。",
    "evidence": "在{halls}选择一件有明确展签的展品，记录材料、形制或纹饰中的一项可见信息。",
    "next": "再把这项观察改写成可核对的问题：哪一处现场信息支持展签中的制作或用途说明？",
}

TOPIC_KEYWORDS = {
    "craft": [
        "陶",
        "器",
        "工艺",
        "纹",
        "材料",
        "制作",
        "烧制",
        "陶窑",
        "尖底瓶",
        "彩陶",
        "石器",
        "骨器",
        "工具",
        "器形",
        "用途",
        "痕迹",
        "磨损",
    ],
    "settlement": [
        "聚落",
        "房屋",
        "半地穴",
        "壕沟",
        "遗址",
        "空间",
        "布局",
        "作坊",
        "灶",
        "墓葬",
        "居住",
        "保护大厅",
        "地面圆形房屋",
    ],
    "social": [
        "社会",
        "组织",
        "分工",
        "规则",
        "共同体",
        "协作",
        "等级",
        "贫富",
        "身份",
        "公共",
        "权力",
        "资源",
        "秩序",
    ],
    "spiritual": ["精神", "信仰", "仪式", "审美", "象征", "人面", "鱼纹", "图案", "纹饰", "祭祀", "观念"],
    "life": ["生活", "吃", "食物", "农业", "农耕", "居住", "日常", "生存", "采集", "狩猎", "儿童", "家庭"],
    "evidence": ["证据", "推断", "不确定", "考古", "展签", "材料", "判断", "线索", "地层", "出土", "遗存"],
}

BEGINNER_PROMPTS = [
    "这件文物让您联想到什么日常生活中的物品？",
    "这件文物最吸引您注意的是什么？",
    "这件文物让您想到了什么故事或传说？",
    "这件文物看起来像什么动物或植物？",
    "这件文物上有什么让您印象深刻的图案或颜色？",
]

INTERMEDIATE_PROMPTS = [
    "这件文物反映的社会结构对今天有什么启示？",
    "这件文物的制作工艺体现了当时怎样的技术水平？",
    "这件文物在当时的社会生活中扮演了什么角色？",
    "这件文物如何反映了当时的审美观念？",
    "这件文物与其他同类文物相比有什么独特之处？",
]

EXPERT_PROMPTS = [
    "现有的考古解读是否存在争议？您倾向于哪种观点？",
    "这件文物的断代依据是否充分？有哪些新的研究方法可以应用？",
    "这件文物的来源和流传过程是否清晰？",
    "这件文物在学术史上的地位如何？有哪些重要的研究成果？",
    "这件文物对于理解当时的文化交流有什么特殊价值？",
]

CATEGORY_REFLECTIONS = {
    "青铜器": [
        "这件青铜器的铸造工艺体现了当时怎样的技术水平？",
        "这件青铜器上的铭文或纹饰有什么特殊含义？",
        "这件青铜器的用途是什么？是礼器、兵器还是生活用具？",
        "这件青铜器的合金比例反映了当时怎样的冶金技术？",
        "这件青铜器与其他地区出土的青铜器有什么异同？",
    ],
    "书画": [
        "这幅作品的笔墨技法有什么独特之处？",
        "这幅作品的构图和意境如何体现了当时的审美追求？",
        "这幅作品的作者生平对其创作风格有什么影响？",
        "这幅作品的题跋和印章提供了哪些历史信息？",
        "这幅作品在书画史上的地位如何？",
    ],
    "陶瓷": [
        "这件陶瓷的釉色和纹饰有什么特点？",
        "这件陶瓷的烧制工艺体现了当时怎样的技术水平？",
        "这件陶瓷的产地和窑口对其价值有什么影响？",
        "这件陶瓷的造型设计反映了当时怎样的生活习俗？",
        "这件陶瓷与其他时期的陶瓷相比有什么演变关系？",
    ],
}

Text = Annotated[str, Field(min_length=1, max_length=2000)]
ShortText = Annotated[str, Field(min_length=1, max_length=100)]
TopicKey = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]


class ReflectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_template(text: str, allowed: set[str]) -> None:
    """Only named scalar slots; attribute traversal and formatting are forbidden."""
    try:
        for _, field, spec, conversion in Formatter().parse(text):
            if field is not None and (field not in allowed or spec or conversion):
                raise ValueError(f"Unsupported template placeholder: {field}")
    except ValueError as exc:
        raise ValueError(f"Invalid text template: {exc}") from exc


class ReflectionLines(ReflectionModel):
    focus: Text
    evidence: Text
    next: Text

    @model_validator(mode="after")
    def validate_templates(self) -> Self:
        for text in (self.focus, self.evidence, self.next):
            validate_template(text, {"halls"})
        return self


class ReflectionTopic(ReflectionLines):
    label: ShortText
    keywords: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(max_length=100)


class ReflectionPersona(ReflectionModel):
    topic: TopicKey
    entry: Text
    theme: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,19}$")]


class ReflectionThresholds(ReflectionModel):
    minimum_signals: int = Field(default=2, ge=1, le=100, strict=True)
    insufficient_confidence: float = Field(default=0.35, ge=0, le=1)
    base_confidence: float = Field(default=0.5, ge=0, le=1)
    topic_confidence_weight: float = Field(default=0.3, ge=0, le=1)
    signal_confidence_weight: float = Field(default=0.03, ge=0, le=1)
    max_confidence: float = Field(default=0.92, ge=0, le=1)
    signal_cap: int = Field(default=6, ge=1, le=100, strict=True)


class RadarDimension(ReflectionModel):
    label: ShortText
    metric: Literal[
        "total_duration_minutes",
        "total_questions",
        "total_exhibits_viewed",
        "site_hall_duration_minutes",
        "ceramic_questions",
    ]
    medium: float = Field(ge=0, le=100000)
    high: float = Field(ge=0, le=100000)
    high_exclusive: bool = True

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        if self.high < self.medium:
            raise ValueError("High radar threshold must be at least the medium threshold")
        return self


RADAR_KEYS = {
    "civilization_resonance",
    "imagination_breadth",
    "history_collection",
    "life_experience",
    "ceramic_aesthetics",
}
GUIDANCE_DEFAULTS = {
    "question_title": "核对一个回答",
    "question_description": "围绕“{question}”，把回答中的结论与展签或实物细节逐项对应。",
    "question_prompt": "回答中的哪一条结论能够由展签、器物形制或现场位置直接验证？",
    "exhibit_title": "回看{subject}",
    "exhibit_description": "先选定材料、形制、纹饰或使用痕迹中的一项，记录能直接看到的细节。",
    "exhibit_prompt": "“{subject}”上哪一处可见细节最能支持展签中的制作或用途说明？",
    "hall_title": "补齐{subject}的观察记录",
    "hall_description": "在{subject}再选一件有明确展签的展品，依次核对材料、形制和使用痕迹。",
    "hall_prompt": "这件展品的材料、形制和使用痕迹分别能确认哪些信息？",
    "empty_title": "建立第一条观察记录",
    "empty_description": "选择一件有明确名称和展签的展品，先记下一项能够直接看到的材料、形制或纹饰信息。",
    "empty_prompt": "哪一处可见细节能够与展签中的制作或用途说明直接对应？",
    "question_summary_title": "把问题变成证据链",
    "question_topic_summary": "你的问题已经落在{topic}上；下一步把问答结论与现场信息逐项对应。",
    "question_summary": "你已经留下具体问题；下一步核对回答中的每项判断来自哪一条现场信息。",
    "viewed_summary_title": "从观察走向提问",
    "viewed_summary": "已有浏览记录可以继续利用；先固定一项可见细节，再提出能够由展签回答的问题。",
    "empty_summary_title": "建立第一条可核对的记录",
    "empty_summary": "从一项能直接看到的细节开始，就能为后续提问和复盘留下清晰线索。",
    "generic_question_step": "把刚才的回答与展签或实物细节对照一下。",
    "question_step": "用展签核对“{question}”的一条答案。",
    "exhibit_step": "回看“{subject}”，记录一处材料或纹饰。",
    "hall_step": "在{subject}选一件展品，记录材料与用途。",
    "empty_step": "选一件有明确展签的展品，记录一处材料或纹饰细节。",
}
ONE_LINER_DEFAULTS = {
    "questions_and_exhibits": "你用{questions}次提问串起了{exhibits}件展品",
    "questions": "你为这次参观留下了{questions}个真实问题",
    "exhibits": "你已经认真看过{exhibits}件展品",
    "minutes": "你为这次参观留下了{minutes}分钟现场记录",
    "empty": "这次参观记录正等待你的下一次发现",
}
STYLE_DEFAULTS = {
    "storytelling": """请以讲故事的方式介绍这件文物，让内容生动有趣、富有感染力。
注重情节的展开和情感的传递，让听众仿佛置身于历史场景之中。
使用生动的语言和形象的比喻，让文物背后的故事活起来。""",
    "academic": """请以学术研究的方式介绍这件文物，内容要严谨、准确、有据可查。
注重历史背景的考证和学术观点的引用，提供可靠的文献依据。
使用专业的术语和规范的表述，确保内容的学术价值和可信度。""",
    "interactive": """请以互动问答的方式介绍这件文物，鼓励观众思考和参与。
提出引人深思的问题，引导观众主动探索和发现。
注重与观众的对话和交流，让参观体验更加生动和有意义。""",
}


def default_topics() -> dict[str, ReflectionTopic]:
    return {
        key: ReflectionTopic(label=label, keywords=TOPIC_KEYWORDS[key], **REVIEW_TOPIC_LINES[key])
        for key, label in REFLECTION_TOPIC_LABELS.items()
    }


def default_personas() -> dict[str, ReflectionPersona]:
    themes = {
        "default": "general",
        "A": "archaeology",
        "B": "field_study",
        "C": "history_inquiry",
        "D": "artifact_study",
    }
    return {
        key: ReflectionPersona(topic=value[0], entry=value[1], theme=themes[key])
        for key, value in PERSONA_REVIEW_ENTRY.items()
    }


def default_radar() -> dict[str, RadarDimension]:
    data = {
        "civilization_resonance": ("参观投入", "total_duration_minutes", 30, 60, True),
        "imagination_breadth": ("提问探索", "total_questions", 10, 15, True),
        "history_collection": ("展品观察", "total_exhibits_viewed", 5, 10, True),
        "life_experience": ("重点展厅体验", "site_hall_duration_minutes", 10, 20, True),
        "ceramic_aesthetics": ("器物细读", "ceramic_questions", 1, 3, False),
    }
    return {
        key: RadarDimension.model_validate(dict(label=v[0], metric=v[1], medium=v[2], high=v[3], high_exclusive=v[4]))
        for key, v in data.items()
    }


class ReflectionConfig(ReflectionModel):
    topics: dict[TopicKey, ReflectionTopic] = Field(default_factory=default_topics, min_length=1, max_length=30)
    personas: dict[str, ReflectionPersona] = Field(default_factory=default_personas, min_length=5, max_length=5)
    event_weights: dict[str, Annotated[float, Field(ge=0, le=100)]] = Field(
        default_factory=lambda: {
            "exhibit_question": 3,
            "exhibit_deep_dive": 3,
            "exhibit_view": 1,
            "hall_enter": 0,
            "hall_leave": 0,
            "default": 0.5,
        },
        min_length=6,
        max_length=6,
    )
    thresholds: ReflectionThresholds = Field(default_factory=ReflectionThresholds)
    identity_tags: dict[str, list[ShortText]] = Field(
        default_factory=lambda: {
            "observation": list(OBSERVATION_TAGS),
            "question": list(QUESTION_TAGS),
            "review": list(REVIEW_TAGS),
        },
        min_length=3,
        max_length=3,
    )
    radar_dimensions: dict[str, RadarDimension] = Field(default_factory=default_radar, min_length=5, max_length=5)
    focused_halls: list[Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,99}$")]] = Field(
        default_factory=lambda: ["site-protection-hall"], max_length=500
    )
    focus_keywords: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(
        default_factory=lambda: list(CERAMIC_KEYWORDS), max_length=100
    )
    insufficient: ReflectionLines = Field(default_factory=lambda: ReflectionLines(**INSUFFICIENT_REVIEW_LINES))
    shifted_template: Text = "把{initial}的初始问题放到{observed}这条线索上继续核对：{next}"
    guidance: dict[str, Text] = Field(default_factory=lambda: dict(GUIDANCE_DEFAULTS))
    one_liners: dict[str, ShortText] = Field(default_factory=lambda: dict(ONE_LINER_DEFAULTS))
    level_prompts: dict[str, list[Text]] = Field(
        default_factory=lambda: {
            "beginner": list(BEGINNER_PROMPTS),
            "intermediate": list(INTERMEDIATE_PROMPTS),
            "expert": list(EXPERT_PROMPTS),
        },
        min_length=3,
        max_length=3,
    )
    narrative_styles: dict[str, Text] = Field(default_factory=lambda: dict(STYLE_DEFAULTS), min_length=3, max_length=3)
    summary_template: Text = "{scope}本次对话主要围绕{topics}展开。记录中的关键结论是：{conclusions}。"
    summary_instruction: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_rules(self) -> Self:
        if set(self.personas) != {"default", "A", "B", "C", "D"}:
            raise ValueError("Reflection personas require default and A/B/C/D")
        if any(persona.topic not in self.topics for persona in self.personas.values()):
            raise ValueError("Reflection persona references an unknown topic")
        if set(self.event_weights) != {
            "exhibit_question",
            "exhibit_deep_dive",
            "exhibit_view",
            "hall_enter",
            "hall_leave",
            "default",
        }:
            raise ValueError("Reflection event weights must contain the supported six keys")
        if set(self.identity_tags) != {"observation", "question", "review"} or any(
            len(tags) != 3 for tags in self.identity_tags.values()
        ):
            raise ValueError("Identity tags require three groups with three tags each")
        if set(self.radar_dimensions) != RADAR_KEYS:
            raise ValueError("Radar dimensions must retain the five API metric keys")
        if set(self.guidance) != set(GUIDANCE_DEFAULTS):
            raise ValueError("Guidance must contain all supported template keys")
        for key, text in self.guidance.items():
            allowed = {field for _, field, _, _ in Formatter().parse(GUIDANCE_DEFAULTS[key]) if field}
            validate_template(text, allowed)
        if set(self.one_liners) != set(ONE_LINER_DEFAULTS):
            raise ValueError("One liners must contain all five states")
        for text in self.one_liners.values():
            validate_template(text, {"questions", "exhibits", "minutes"})
        validate_template(self.shifted_template, {"initial", "observed", "next"})
        validate_template(self.summary_template, {"scope", "topics", "conclusions"})
        if set(self.level_prompts) != {"beginner", "intermediate", "expert"} or any(
            not 1 <= len(prompts) <= 20 for prompts in self.level_prompts.values()
        ):
            raise ValueError("Each knowledge level requires 1–20 reflection prompts")
        if set(self.narrative_styles) != {"storytelling", "academic", "interactive"}:
            raise ValueError("All three narrative styles are required")
        return self
