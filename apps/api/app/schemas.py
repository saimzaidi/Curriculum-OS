from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CourseCreate(BaseModel):
    name: str = Field(min_length=2)
    grade: str = Field(min_length=1)
    subject: str = Field(min_length=2)
    section: str = Field(min_length=1)
    language: str = "English"
    localization_region: str = "Karachi, Pakistan"


class SignUp(BaseModel):
    email: str
    password: str
    display_name: str = Field(min_length=2, max_length=100)


class SignIn(BaseModel):
    email: str
    password: str


class CalendarInput(BaseModel):
    start_date: date
    end_date: date
    exam_date: date
    session_days: list[Literal["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]]
    session_minutes: int = Field(ge=5, le=300)
    holidays: list[date] = Field(default_factory=list)
    revision_sessions: int = Field(default=2, ge=0)

    @field_validator("end_date")
    @classmethod
    def ends_after_start(cls, end_date: date, info):
        if "start_date" in info.data and end_date < info.data["start_date"]:
            raise ValueError("end_date must not precede start_date")
        return end_date


class ConceptEdit(BaseModel):
    title: str = Field(min_length=2)
    description: str = Field(min_length=2)
    difficulty: int = Field(ge=1, le=5)
    estimated_minutes: int = Field(ge=5, le=600)
    required: bool = True
    exam_weight: float = Field(default=0.5, ge=0, le=1)
    source_block_ids: list[str] = Field(min_length=1)
    learning_objectives: list[str] = Field(min_length=1)
    confidence: float = Field(default=1, ge=0, le=1)
    locked: bool = False


class SourceBlockEdit(BaseModel):
    text: str = Field(min_length=1, max_length=50000)


class ReplanRequest(BaseModel):
    base_version_id: str
    cancelled_session_ids: list[str] = Field(default_factory=list)
    preserve_locked_items: bool = True
    minimize_disruption: bool = True


class LessonGenerateRequest(BaseModel):
    language: str = "en"
    localization_region: str = "Karachi, Pakistan"
    levels: list[Literal["below", "on", "advanced"]] = ["below", "on", "advanced"]
    include_activity: bool = True
    include_homework: bool = True


class AssessmentGenerateRequest(BaseModel):
    concept_ids: list[str] = Field(min_length=1)
    title: str = "Source-grounded check"
