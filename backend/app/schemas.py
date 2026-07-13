from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Track = Literal["mle", "ai4s", "swe_newgrad", "career_switch"]
Level = Literal["junior", "mid", "senior"]
Platform = Literal["leetcode_cn", "leetcode_com"]
Outcome = Literal["ac_first_try", "ac", "failed", "abandoned"]

MISTAKE_TAGS = [
    "misread_problem", "edge_case_missed", "off_by_one", "wrong_data_structure",
    "pattern_not_recognized", "complexity_misjudged", "recursion_base_case",
    "dp_state_definition", "implementation_bug", "numerical_stability", "api_unfamiliar",
]


# --- profile ---------------------------------------------------------------


class ProfileIn(BaseModel):
    name: str = "me"
    background: str = ""
    target_track: Track = "mle"
    target_level: Level = "junior"
    timeline_weeks: int | None = None
    weekly_hours: int = Field(ge=1, le=80)
    preferred_lang: str = "python"
    platform: Platform = "leetcode_cn"
    include_primers: bool = False


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# --- problems ---------------------------------------------------------------


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track: str
    lc_id: int | None
    slug: str
    title: str
    difficulty: str
    patterns: list[str]
    importance: int


# --- plan -------------------------------------------------------------------


class PlanReviewItem(BaseModel):
    problem: ProblemOut
    url: str
    due_date: date
    overdue_days: int
    review_count: int
    mastery: str


class PlanNewItem(BaseModel):
    problem: ProblemOut
    url: str
    is_primer: bool
    is_stale_learning: bool


class TodayPlanOut(BaseModel):
    reviews: list[PlanReviewItem]
    new: list[PlanNewItem]
    budget_minutes: int
    streak: int


# --- attempts ---------------------------------------------------------------


class AttemptStartIn(BaseModel):
    problem_id: int


class AttemptFinishIn(BaseModel):
    outcome: Outcome
    duration_sec: int = Field(ge=0)
    recall_self_report: float = Field(ge=0, le=5)
    mistake_tags: list[str] = []
    code_snapshot: str | None = None
    self_explanation: str | None = None
    judge_failures: int = Field(default=0, ge=0)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    problem_id: int
    ease_factor: float
    interval_days: int
    due_date: date
    review_count: int
    last_quality: float | None
    mastery: str


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: int
    started_at: datetime
    outcome: str | None
    hint_level_max: int
    judge_failures: int
    duration_sec: int | None
    mistake_tags: list[str]


class AttemptFinishOut(BaseModel):
    attempt: AttemptOut
    review: ReviewOut | None  # None for primers (they skip spaced repetition)
    quality: float | None


# --- hints ------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class HintIn(BaseModel):
    attempt_id: int
    level: int = Field(ge=1, le=4)
    messages: list[ChatMessage] = []


# --- stats ------------------------------------------------------------------


class PatternProgress(BaseModel):
    pattern: str
    solved: int
    total: int


class DifficultyProgress(BaseModel):
    difficulty: str
    solved: int
    total: int


class StatsOut(BaseModel):
    pattern_progress: list[PatternProgress]
    difficulty_progress: list[DifficultyProgress]
    streak: int
    heatmap: dict[str, int]  # ISO date -> finished attempts
    total_solved: int
    total_attempts: int
    ac_first_try_rate: float | None
    avg_hint_level_30d: float | None
