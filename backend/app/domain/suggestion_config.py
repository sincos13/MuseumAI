"""Museum-specific suggestion vocabulary and bounded question templates.

Presentation quality checks remain in the application and cannot be disabled by
museum content. Templates never interpolate arbitrary Python expressions.
"""

from string import Formatter
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SuggestionWord = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
SuggestionTemplate = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]

_DEFAULT_DESCRIPTION_ANCHORS = [
    ("人面鱼纹", "人面鱼纹"),
    ("刻划符号", "陶器刻痕"),
    ("碳化谷粒", "烧焦的谷粒"),
    ("炭化木椽", "烧黑的木椽"),
    ("颜料残留", "颜料痕迹"),
    ("墓葬区", "墓区"),
    ("陶窑区", "陶窑区"),
    ("居住区", "住屋区"),
    ("使用痕迹", "磨损"),
    ("随葬品", "随葬品"),
    ("谷壳层", "谷壳"),
    ("草泥层", "草泥墙"),
    ("柱洞", "柱洞"),
    ("壕沟", "壕沟"),
    ("火膛", "火膛"),
    ("窑室", "窑室"),
    ("窑箅", "窑床"),
    ("穿孔", "小孔"),
    ("倒刺", "倒刺"),
    ("磨痕", "磨痕"),
    ("耳孔", "耳孔"),
    ("尖底", "尖底"),
    ("小口", "小口"),
    ("网纹", "网纹"),
    ("席纹", "席纹"),
    ("鱼纹", "鱼纹"),
    ("鹿纹", "鹿纹"),
    ("骨骼", "骨头"),
    ("火道", "火道"),
    ("灶台", "灶台"),
    ("窖穴", "窖穴"),
    ("榫卯", "木头接头"),
    ("陶片", "陶片"),
    ("纺轮", "纺轮"),
]

_DEFAULT_SUBJECT_NOISE_PREFIXES = ["西安半坡博物馆", "新石器时代", "仰韶文化", "半坡文化", "半坡遗址", "馆藏", "出土"]

_DEFAULT_SUBJECT_NOISE_SUFFIXES = ["复制品", "修复件", "复原件", "展品", "标本", "藏品", "之谜", "集萃"]

_DEFAULT_SUBJECT_OBJECT_ENDINGS = [
    "人面鱼纹彩陶盆",
    "小口尖底瓶",
    "彩陶盆",
    "尖底瓶",
    "陶罐",
    "陶钵",
    "陶壶",
    "陶盆",
    "陶瓶",
    "石斧",
    "石刀",
    "骨针",
    "骨锥",
    "骨铲",
    "纺轮",
    "网坠",
    "鱼钩",
    "陶窑",
    "房址",
    "墓葬",
    "壕沟",
    "灶址",
    "遗址",
    "雕塑",
    "模型",
    "陶片",
    "骨器",
    "石器",
    "陶器",
    "器物",
    "工具",
]

_DEFAULT_SUBJECT_MODIFIER_TERMS = [
    "人面鱼纹",
    "兽面纹",
    "彩绘",
    "高足",
    "小口",
    "尖底",
    "陶质",
    "石质",
    "骨质",
    "磨制",
    "穿孔",
]

_DEFAULT_SITE_SUBJECT_MARKERS = ["房址", "墓葬", "遗址", "号墓", "灰坑", "窖穴", "壕沟", "柱洞", "灶址"]

_DEFAULT_DISPLAY_SUBJECT_MARKERS = ["雕塑", "模型", "分布图", "平面图", "复原图", "示意图"]

_DEFAULT_FRAGMENT_SUBJECT_MARKERS = ["残片", "碎片", "陶片", "骨片"]

_DEFAULT_TOOL_OR_ARTIFACT_MARKERS = [
    "盆",
    "瓶",
    "罐",
    "钵",
    "壶",
    "斧",
    "刀",
    "针",
    "锥",
    "铲",
    "纺轮",
    "网坠",
    "鱼钩",
    "骨器",
    "石器",
    "陶器",
    "器物",
    "工具",
]

_DEFAULT_STRONG_DETAIL_ANCHORS = [
    "人面鱼纹",
    "倒刺",
    "小口",
    "小孔",
    "尖底",
    "席纹",
    "榫卯",
    "烧焦的谷粒",
    "烧黑的木椽",
    "磨损",
    "磨痕",
    "网纹",
    "草泥墙",
    "陶器刻痕",
    "陶片",
    "随葬品",
    "颜料痕迹",
    "鱼纹",
    "鹿纹",
]

_DEFAULT_TEMPLATES = {
    "fragment": ["{subject}具体是什么？", "{subject}保留了什么？"],
    "display": ["{subject}展示了什么？", "{subject}表现了什么？"],
    "site": ["{subject}发现了什么？", "{subject}能看出什么？"],
    "kiln": ["{subject}怎样烧陶器？", "{subject}结构怎么看？"],
    "artifact": ["{subject}当时怎么用？", "{subject}是怎么做的？"],
    "inventory": ["{subject}是什么？"],
    "default": ["{subject}具体是什么？", "{subject}能看出什么？"],
    "anchor_mark": ["{anchor}记了什么？"],
    "anchor_pattern": ["{anchor}画的是什么？"],
    "anchor_trace": ["{anchor}是怎么留下的？"],
    "anchor_default": ["{anchor}主要有什么用？"],
}


class SuggestionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    description_anchors: list[tuple[SuggestionWord, SuggestionWord]] = Field(
        default_factory=lambda: list(_DEFAULT_DESCRIPTION_ANCHORS), max_length=200
    )
    subject_noise_prefixes: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_SUBJECT_NOISE_PREFIXES), max_length=200
    )
    subject_noise_suffixes: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_SUBJECT_NOISE_SUFFIXES), max_length=200
    )
    subject_object_endings: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_SUBJECT_OBJECT_ENDINGS), max_length=200
    )
    subject_modifier_terms: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_SUBJECT_MODIFIER_TERMS), max_length=200
    )
    site_subject_markers: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_SITE_SUBJECT_MARKERS), max_length=200
    )
    display_subject_markers: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_DISPLAY_SUBJECT_MARKERS), max_length=200
    )
    fragment_subject_markers: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_FRAGMENT_SUBJECT_MARKERS), max_length=200
    )
    tool_or_artifact_markers: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_TOOL_OR_ARTIFACT_MARKERS), max_length=200
    )
    strong_detail_anchors: list[SuggestionWord] = Field(
        default_factory=lambda: list(_DEFAULT_STRONG_DETAIL_ANCHORS), max_length=200
    )
    anchor_mark_markers: list[SuggestionWord] = Field(default_factory=lambda: ["刻痕"], max_length=200)
    anchor_pattern_endings: list[SuggestionWord] = Field(default_factory=lambda: ["纹", "花纹"], max_length=200)
    anchor_trace_markers: list[SuggestionWord] = Field(
        default_factory=lambda: ["痕", "磨损", "谷粒", "木椽", "骨头", "陶片", "谷壳"], max_length=200
    )
    kiln_subject_markers: list[SuggestionWord] = Field(default_factory=lambda: ["陶窑"], max_length=200)
    question_templates: dict[str, list[SuggestionTemplate]] = Field(
        default_factory=lambda: {key: list(value) for key, value in _DEFAULT_TEMPLATES.items()},
        min_length=11,
        max_length=11,
    )

    @model_validator(mode="after")
    def validate_templates(self) -> Self:
        if set(self.question_templates) != set(_DEFAULT_TEMPLATES):
            raise ValueError("Suggestion question_templates must include all supported template groups")
        for group, templates in self.question_templates.items():
            if not 1 <= len(templates) <= 6:
                raise ValueError("Each suggestion template group requires one to six templates")
            placeholder = "anchor" if group.startswith("anchor_") else "subject"
            for template in templates:
                try:
                    fields = list(Formatter().parse(template))
                except ValueError as exc:
                    raise ValueError("Invalid suggestion template braces") from exc
                if any(
                    name is not None and (name != placeholder or spec or conversion)
                    for _, name, spec, conversion in fields
                ):
                    raise ValueError(f"Suggestion {group} templates only support {{{placeholder}}}")
                if not any(name == placeholder for _, name, _, _ in fields):
                    raise ValueError("Suggestion template must name the concrete subject or anchor")
                if not template.endswith("？"):
                    raise ValueError("Suggestion templates must end with a Chinese question mark")
        return self
