"""Museum-editable experience preferences; persona prompts remain authoritative."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GuideShortcut(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")
    label: str = Field(min_length=1, max_length=40)
    question: str = Field(min_length=1, max_length=300)
    requires_any: list[str] = Field(default_factory=list, max_length=12)
    asked_phrases: list[str] = Field(default_factory=list, max_length=16)


class GuideExperience(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    method: str = Field(default="遵循身份指令，围绕一个具体看点接续游客的回应。", min_length=1, max_length=800)
    shortcuts: list[GuideShortcut] = Field(default_factory=list, max_length=8)
    takeaway_title: str = Field(min_length=1, max_length=80)
    takeaway_instruction: str = Field(min_length=1, max_length=1200)
    section_labels: list[str] = Field(min_length=3, max_length=3)
    selection_keywords: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def valid_preferences(self):
        if len({item.id for item in self.shortcuts}) != len(self.shortcuts):
            raise ValueError("Shortcut IDs must be unique within a persona")
        if any(not label.strip() or len(label) > 50 for label in self.section_labels):
            raise ValueError("Report section labels must contain 1–50 characters")
        if any(not word.strip() or len(word) > 40 for word in self.selection_keywords):
            raise ValueError("Selection keywords must contain 1–40 characters")
        for item in self.shortcuts:
            if any(not word.strip() or len(word) > 40 for word in item.requires_any):
                raise ValueError("Shortcut keywords must contain 1–40 characters")
            if any(not word.strip() or len(word) > 80 for word in item.asked_phrases):
                raise ValueError("Asked phrases must contain 1–80 characters")
        return self


def default_guide_experience(code: str) -> GuideExperience:
    choices = {
        "A": (
            "我的证据札记",
            ["讨论的判断", "已有依据", "仍缺的证据"],
            "优先选择游客的猜想、依据、质疑与不同解释。把判断、来源依据和证据缺口分开。",
            ["觉得", "可能", "依据", "证据", "判断", "确定", "解释"],
            [
                ("evidence", "依据在哪里", "{exhibit}的这个判断有哪些资料依据？", []),
                ("alternatives", "还有其他解释吗", "关于{exhibit}刚才的解释，资料能支持其他解释吗？", []),
                ("unknown", "还缺什么证据", "要进一步理解{exhibit}，现有资料还缺什么证据？", []),
            ],
        ),
        "B": (
            "我的学习便笺",
            ["核心知识", "自己的表达", "还想问的问题"],
            "优先选择游客自己的表述、理解困难和复述。自己的表达必须引用原话，不能替游客说已经理解。",
            ["理解", "意思", "我觉得", "我看到", "是不是", "不懂", "记"],
            [
                ("simple", "换个容易懂的说法", "请用容易懂的说法解释{exhibit}刚才的要点。", []),
                ("notes", "帮我整理重点", "把我们关于{exhibit}的讨论整理成一条容易记住的笔记。", []),
                ("question", "留一个待解的问题", "关于{exhibit}，资料还有哪个具体问题没有回答？", []),
            ],
        ),
        "C": (
            "我的问题线索",
            ["起点问题", "关联材料", "继续追问的方向"],
            "优先选择从展品进入生活、需求、组织与历史背景的提问。联系只能使用已记录的资料，不编造故事。",
            ["为什么", "生活", "人", "需求", "变化", "关系", "怎样"],
            [
                ("life", "与当时生活有什么关系", "{exhibit}与当时人的哪些生活需求有关？请结合资料说明。", []),
                (
                    "change",
                    "为什么会有这种变化",
                    "资料记录了{exhibit}的哪些变化，能解释变化的原因吗？",
                    ["变化", "修", "替换", "改", "发展"],
                ),
                ("connection", "把问题接着问下去", "从{exhibit}刚才的讨论出发，还有什么值得继续追问的生活问题？", []),
            ],
        ),
        "D": (
            "我的器物观察卡",
            ["讨论过的细节", "相关解释", "尚不确定的地方"],
            "优先选择对材料、结构、纹饰、工艺与用途的具体讨论。把游客描述与馆方记载分开，不补齐未讨论的属性。",
            ["材料", "口", "结构", "纹", "痕", "制作", "用途", "形"],
            [
                ("detail", "先看哪个部位", "{exhibit}有哪些资料明确记载、值得先看的细节？一次只讲一个。", []),
                (
                    "structure",
                    "这种结构有什么作用",
                    "{exhibit}已知的形状或结构与用途有什么关系？",
                    ["口", "形", "结构", "柄", "边", "孔", "连接"],
                ),
                (
                    "material",
                    "材料怎样影响使用",
                    "{exhibit}的材料怎样影响制作或使用？区分一般原理与本件事实。",
                    ["材", "陶", "木", "铜", "石", "纸", "竹"],
                ),
            ],
        ),
    }
    title, labels, instruction, keywords, shortcuts = choices.get(code, choices["A"])
    return GuideExperience(
        method={
            "A": "围绕一个具体判断找证据：先指出资料中的线索，区分已知与推测，邀请游客判断这条线索能支持什么。",
            "B": "把知识拆成一小步：先用白话解释一个细节，邀请游客用自己的话描述或复述，接着帮他整理清楚。",
            "C": "从展品进入人的生活问题：选择资料支持的使用、维护或组织需求，让游客联系生活并追问原因。",
            "D": "从器物部位进入：优先选资料记载的口沿、接口、纹饰或材料细节，把形态与制作或用途联系起来。",
        }.get(code, "遵循身份指令，围绕一个具体看点接续游客的回应。"),
        takeaway_title=title,
        section_labels=labels,
        takeaway_instruction=instruction,
        selection_keywords=keywords,
        shortcuts=[GuideShortcut(id=key, label=label, question=q, requires_any=k,
                                 asked_phrases=DEFAULT_ASKED_PHRASES.get(key, []))
                   for key, label, q, k in shortcuts],
    )


# Conservative phrases mark a topic the visitor has already chosen. They do not
# classify a casual observation (e.g. “开口比较小”) as a question about function.
DEFAULT_ASKED_PHRASES = {
    "evidence": ["依据在哪", "依据是什么", "什么依据", "哪些依据", "什么证据", "哪些证据"],
    "alternatives": ["其他解释", "别的解释", "另一种解释"],
    "unknown": ["缺什么证据", "缺哪些证据", "缺少什么证据"],
    "simple": ["容易懂的说法", "简单解释", "说得简单", "通俗一点"],
    "notes": ["整理重点", "整理成笔记", "帮我记下来"],
    "life": ["与当时生活", "和当时生活", "哪些生活需求", "什么生活需求"],
    "change": ["为什么会有这种变化", "为什么发生变化"],
    "detail": ["先看哪个部位", "先看什么细节", "先看哪里"],
    "structure": ["结构有什么作用", "结构有什么用", "开口有什么用", "口径与用途"],
    "material": ["材料怎样影响", "材料如何影响", "材料有什么影响"],
}
