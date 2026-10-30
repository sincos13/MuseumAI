"""Optional museum-owned visitor content; runtime identities stay in the database."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Short = Annotated[str, StringConstraints(min_length=1, max_length=255)]
Paragraph = Annotated[str, StringConstraints(min_length=1, max_length=2000)]


class VisitorContent(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VisitorStop(VisitorContent):
    hall_slug: Short
    minutes: int = Field(ge=1, le=480)
    exhibit_ids: list[Short] = Field(min_length=1, max_length=20)
    task: Paragraph


class InterestStop(VisitorContent):
    hall_slug: Short
    exhibit_ids: list[Short] = Field(min_length=1, max_length=20)


class VisitorRoute(VisitorContent):
    id: Short
    persona: Literal["A", "B", "C", "D"]
    planned_minutes: int = Field(ge=1, le=1440)
    intro_minutes: int = Field(ge=0, le=120)
    transfer_minutes: int = Field(ge=0, le=120)
    report_minutes: int = Field(ge=0, le=120)
    buffer_minutes: int = Field(ge=0, le=120)
    steps: list[VisitorStop] = Field(min_length=1, max_length=50)
    interest_variants: dict[str, list[InterestStop]] = Field(default_factory=dict, max_length=20)

    @model_validator(mode="after")
    def consistent_budget(self):
        extra = self.intro_minutes + self.transfer_minutes + self.report_minutes + self.buffer_minutes
        if sum(step.minutes for step in self.steps) + extra != self.planned_minutes:
            raise ValueError("Visitor route budget does not match planned minutes")
        slugs = [step.hall_slug for step in self.steps]
        if len(set(slugs)) != len(slugs):
            raise ValueError("Visitor route repeats a hall")
        for variant in self.interest_variants.values():
            if [step.hall_slug for step in variant] != slugs:
                raise ValueError("Interest variant must keep the route hall order")
        return self


class VisitorExhibit(VisitorContent):
    source_record_id: Short
    hall_slug: Short
    aliases: list[Short] = Field(default_factory=list, max_length=30)
    material: str = Field(default="", max_length=500)
    size: str = Field(default="", max_length=500)
    introduction: Paragraph
    observation_task: Paragraph
    guide_question: Short
    unknown: Paragraph
    image_caption: str = Field(default="", max_length=500)
    related_ids: list[Short] = Field(default_factory=list, max_length=20)
    relation_explanation: Paragraph


class VisitorExperience(VisitorContent):
    version: Literal[1] = 1
    disclosure: str = Field(default="", max_length=1000)
    focus_to_persona: dict[str, Literal["A", "B", "C", "D"]] = Field(
        default_factory=lambda: {"A": "B", "B": "A", "C": "C", "D": "D"}, max_length=4
    )
    rhythm_minutes: dict[str, int] = Field(default_factory=dict, max_length=20)
    hall_openings: dict[str, Paragraph] = Field(default_factory=dict, max_length=500)
    routes: list[VisitorRoute] = Field(default_factory=list, max_length=100)
    exhibits: list[VisitorExhibit] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def unique_content(self):
        if set(self.focus_to_persona) != set("ABCD"):
            raise ValueError("Visitor focus mapping requires A, B, C, D")
        if any(isinstance(value, bool) or not 1 <= value <= 1440 for value in self.rhythm_minutes.values()):
            raise ValueError("Invalid rhythm duration")
        for items in ([r.id for r in self.routes], [e.source_record_id for e in self.exhibits]):
            if len(items) != len(set(items)):
                raise ValueError("Duplicate visitor content identity")
        return self
