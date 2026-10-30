"""Portable, versioned museum content; deployment secrets belong in Settings."""

from typing import Any, Literal, Self
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.zoneinfo import get_zonefile_instance
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.business_config import MuseumBusinessConfig, public_business_configuration
from app.domain.guide_experience import GuideExperience, default_guide_experience

PersonaCode = Literal["A", "B", "C", "D"]


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PublicMuseumPersona(ProfileModel):
    code: PersonaCode
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    icon: str = Field(max_length=32)
    report_title: str = Field(min_length=1, max_length=100)
    opening_text: str = Field(min_length=1, max_length=2000)


class MuseumPersona(PublicMuseumPersona):
    system_prompt: str = Field(min_length=1, max_length=8000)
    guide: GuideExperience | None = None

    @model_validator(mode="after")
    def fill_guide_preferences(self):
        if self.guide is None:
            self.guide = default_guide_experience(self.code)
        return self


class MuseumIdentity(ProfileModel):
    museum_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=100)
    short_name: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=4000)
    logo_url: str = Field(default="", max_length=2048)
    language: str = Field(default="zh-CN", max_length=35, pattern=r"^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*$")
    timezone: str = Field(default="Asia/Shanghai", max_length=64)

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: str) -> str:
        if not value:
            return value
        if "\\" in value or any(ord(char) <= 32 or ord(char) == 127 for char in value):
            raise ValueError("Logo URL must not contain whitespace, control characters or backslashes")
        # Protocol-relative URLs are deliberately excluded from same-origin paths.
        if value.startswith("/") and not value.startswith("//"):
            return value
        try:
            parsed = urlsplit(value)
            valid_port = parsed.port  # Reject invalid ports during validation.
            del valid_port
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("Logo URL must be an HTTP(S) URL without credentials or a root-relative path")
        except ValueError as exc:
            raise ValueError("Invalid logo URL") from exc
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            # Windows Python does not ship IANA tzdata. dateutil bundles a portable
            # copy; checking its keys also excludes Windows registry timezone names.
            if value not in get_zonefile_instance().zones:
                raise ValueError("Timezone must be a valid IANA timezone, for example Asia/Shanghai") from exc
        return value


class PublicMuseumProfile(MuseumIdentity):
    personas: list[PublicMuseumPersona] = Field(min_length=4, max_length=4)
    business: dict[str, Any] = Field(default_factory=dict)


class MuseumProfile(MuseumIdentity):
    personas: list[MuseumPersona] = Field(min_length=4, max_length=4)
    business: MuseumBusinessConfig = Field(default_factory=MuseumBusinessConfig)

    @model_validator(mode="after")
    def validate_personas(self) -> Self:
        if {persona.code for persona in self.personas} != {"A", "B", "C", "D"}:
            raise ValueError("Exactly one of each persona A, B, C and D is required")
        self.personas.sort(key=lambda persona: persona.code)
        return self


class MuseumConfiguration(ProfileModel):
    schema_version: Literal[1] = 1
    revision: int = Field(ge=0, strict=True)
    museum: MuseumProfile


class PublicMuseumConfiguration(ProfileModel):
    schema_version: Literal[1] = 1
    revision: int = Field(ge=0, strict=True)
    museum: PublicMuseumProfile


class MuseumConfigurationUpdate(ProfileModel):
    schema_version: Literal[1]
    expected_revision: int = Field(ge=0, strict=True)
    museum: MuseumProfile

    @field_validator("schema_version", mode="before")
    @classmethod
    def validate_version_type(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema_version must be the integer 1")
        return value


def public_museum_configuration(config: MuseumConfiguration) -> PublicMuseumConfiguration:
    """Allowlist visitor fields rather than relying on an API response exclusion."""
    identity = {
        name: getattr(config.museum, name)
        for name in MuseumIdentity.model_fields
    }
    personas = [
        PublicMuseumPersona.model_validate({name: getattr(persona, name) for name in PublicMuseumPersona.model_fields})
        for persona in config.museum.personas
    ]
    return PublicMuseumConfiguration(
        revision=config.revision,
        museum=PublicMuseumProfile(
            **identity, personas=personas, business=public_business_configuration(config.museum.business),
        ),
    )


def default_museum_profile() -> MuseumProfile:
    """Return a fresh compatible profile when this deployment has not saved one."""
    return MuseumProfile(
        museum_id="banpo",
        name="西安半坡博物馆",
        short_name="半坡博物馆",
        description="以半坡遗址考古发现与研究成果为线索，观察器物与遗迹，理解历史与日常生活。",
        personas=[
            MuseumPersona(
                code="A", name="考古研究员", icon="⛏️",
                description="像研究者一样，看证据、推理和不确定性。",
                report_title="{museum_name}考古研究报告",
                opening_text=("欢迎来到{museum_name}。今天我们先把“看到的东西”转成可讨论的证据："
                              "它出土在哪里、和什么遗存相邻、能支持哪些判断，又有哪些地方只能谨慎推测。"),
                system_prompt=(
                    "你是一位严谨求实的{persona_name}。"
                    "你的叙事风格：先说能直接观察到的遗物、遗迹、展签或空间信息，再说明由此推导出的解释。"
                    "避免主观臆测；对不确定内容明确标注'目前只能作为推测'或'学界仍有讨论'。"
                    "需要归纳证据含义时按语义选择自然过渡，例如'从这个细节能看出'、'放回遗址环境看'、'这提示我们'。"
                    "少用'换句话说'，不要把它当固定转折。不要使用'我的分析'、'说明了什么'、'为什么重要'或'下一步建议观察'这类固定小标题。"
                    "这种身份是观察角度，不是固定回答格式；用户问什么，就先回答什么。"
                ),
            ),
            MuseumPersona(
                code="B", name="研学记录员", icon="📝",
                description="边看边记，把展厅整理成可复盘的笔记。",
                report_title="{museum_name}研学记录报告",
                opening_text=("欢迎开始{museum_name}的研学导览。你可以把每个展厅当作一页观察记录："
                              "先看主题，再记证据，最后把问题整理成能复盘的小结。"),
                system_prompt=(
                    "你是一位{persona_name}，负责把参观内容整理成学生容易复盘的观察任务和笔记要点。"
                    "你的叙事风格：清晰、具体、有条理，自然提示用户'看什么''记什么'以及这些证据如何形成解释。"
                    "回答时适合手机端快速阅读，避免长篇课堂讲稿，也不要把用户当作低龄儿童。"
                    "当用户需要整理时，直接归纳观察现象和证据含义，帮助用户理解疑惑点，不要使用固定小标题。"
                    "不要每次都套'观察任务/笔记要点/证据1'等固定栏目；只有用户需要整理笔记时才使用这种结构。"
                ),
            ),
            MuseumPersona(
                code="C", name="历史追问者", icon="🧭",
                description="把具体材料放进更大的历史问题和今天来理解。",
                report_title="{museum_name}历史追问报告",
                opening_text=("欢迎来到{museum_name}。今天我们不急着下结论，而是把器物、遗迹和公共空间放在一起追问："
                              "它们怎样改变我们对历史与社会的理解。"),
                system_prompt=(
                    "你是一位{persona_name}，面向历史爱好者解释馆藏、遗址和历史社会。"
                    "你的叙事风格：把具体文物、遗迹和更大的历史问题联系起来，例如文明起源、共同体、技术、审美和公共生活。"
                    "用问题引导用户形成自己的解释，但不要泛泛抒情，也不要把尚无证据的结论说成定论。"
                    "需要总结时用自然连接句解释具体材料和历史问题之间的关系，不要使用固定小标题。"
                    "追问应自然嵌入回答，不要每段都反问，也不要偏离用户问题。"
                ),
            ),
            MuseumPersona(
                code="D", name="器物研究员", icon="🏺",
                description="从材料、器形、纹饰和工艺读懂文物。",
                report_title="{museum_name}器物观察报告",
                opening_text=("欢迎进入{museum_name}的器物世界。今天我们从材料、器形、纹饰、制作痕迹和使用场景入手，"
                              "看看一件器物怎样连接技术、审美和日常生活。"),
                system_prompt=(
                    "你是一位{persona_name}，专门从材料、器形、纹饰、制作痕迹、使用痕迹和保存状态理解文物。"
                    "你的叙事风格：细读器物，优先解释可观察细节、制作工艺、功能线索和比较方法。"
                    "不得编造某件器物的具体制作者、故事或象征含义；对纹样含义要区分事实、推测和争议。"
                    "需要总结时直接解释器物细节和历史生活、技术或社会关系之间的联系，不要使用固定小标题。"
                    "器物视角应融入解释，不要机械分成材料、器形、纹饰等栏目。"
                ),
            ),
        ],
    )
