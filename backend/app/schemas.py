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
    avatar_url: str | None = None


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


class ProblemDetail(ProblemOut):
    """Single-problem view — ML problems carry their statement and test spec."""

    statement: str | None = None
    test_spec: dict | None = None


# --- plan -------------------------------------------------------------------

PlanKind = Literal["review", "new", "bonus"]


class PlanItemOut(BaseModel):
    problem: ProblemOut
    url: str
    kind: PlanKind
    done: bool
    stale: bool = False  # mastery 'learning', untouched 3+ days
    # review-only metadata
    due_date: date | None = None
    overdue_days: int | None = None
    review_count: int | None = None
    mastery: str | None = None


class TodayPlanOut(BaseModel):
    items: list[PlanItemOut]  # frozen for the day; bonus items appended at the end
    done_count: int  # completed among review+new (bonus excluded)
    total_count: int  # review+new count
    bonus_done: int
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


# --- code review (M2, §8.3) ---------------------------------------------------


class ReviewCodeIn(BaseModel):
    attempt_id: int


class ComplexityVerdict(BaseModel):
    claimed: str | None = None
    actual: str


class ReviewCodeOut(BaseModel):
    correctness_risks: list[str] = []
    complexity: ComplexityVerdict
    style_issues: list[str] = []
    optimal_comparison: str = ""
    mistake_tags_suggested: list[str] = []


class ConfirmTagsIn(BaseModel):
    tags: list[str]


# --- teach-back (M2, §8.4) ----------------------------------------------------


class TeachbackIn(BaseModel):
    attempt_id: int
    transcript: list[ChatMessage] = Field(min_length=1)


class TeachbackOut(BaseModel):
    passed: bool
    gaps: list[str] = []
    follow_up_question: str | None = None


class TeachbackResult(TeachbackOut):
    mastery: str | None = None  # review state after this round (None for primers)


# --- weaknesses (M2) -----------------------------------------------------------


class TagStatOut(BaseModel):
    tag: str
    count: int
    weighted: float
    rate: float


class PatternStatOut(BaseModel):
    pattern: str
    attempts: int
    error_rate: float


class WeaknessOut(BaseModel):
    tags: list[TagStatOut]
    patterns: list[PatternStatOut]
    weak_patterns: list[str]


# --- reports (M2, §8.5) ---------------------------------------------------------


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_start: date
    period_end: date
    content_md: str
    metrics: dict
    created_at: datetime


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_start: date
    period_end: date
    created_at: datetime


# --- mock interview (M3, §8.2) --------------------------------------------------

Verdict = Literal["strong_hire", "hire", "lean_hire", "no_hire"]

MOCK_DURATION_SEC = 45 * 60


class MockStartIn(BaseModel):
    problem_id: int | None = None  # None -> weakness-biased random pick


class MockProblemOut(BaseModel):
    """Interviewer only announces number + title — no patterns (would spoil)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    lc_id: int | None
    title: str


class MockStartOut(BaseModel):
    session_id: int
    problem: MockProblemOut
    opening: str
    duration_sec: int = MOCK_DURATION_SEC


class MockMessageIn(BaseModel):
    session_id: int
    message: str = Field(min_length=1)


class MockRubric(BaseModel):
    communication: int = Field(ge=1, le=5)
    problem_solving: int = Field(ge=1, le=5)
    code_correctness: int = Field(ge=1, le=5)
    complexity_analysis: int = Field(ge=1, le=5)
    edge_cases: int = Field(ge=1, le=5)
    time_management: int = Field(ge=1, le=5)


class MockDrill(BaseModel):
    pattern: str
    count: int = 3
    instruction: str


class MockEvaluation(BaseModel):
    """LLM output schema for /mock/finish (§8.2)."""

    rubric: MockRubric
    verdict: Verdict
    postmortem: str
    drills: list[MockDrill] = []


class MockFinishIn(BaseModel):
    session_id: int
    duration_sec: int = Field(ge=0)
    code: str | None = None  # final content of the plain-text code box


class MockSessionOut(BaseModel):
    id: int
    problem: MockProblemOut
    transcript: list[ChatMessage]
    duration_sec: int | None
    rubric: MockRubric | None
    verdict: str | None
    postmortem: str | None
    drills: list[MockDrill] | None
    created_at: datetime


class MockSessionSummary(BaseModel):
    id: int
    problem: MockProblemOut
    verdict: str | None
    rubric_avg: float | None
    created_at: datetime


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
