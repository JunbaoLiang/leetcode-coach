from datetime import UTC, date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    background: Mapped[str] = mapped_column(Text, default="")
    target_track: Mapped[str] = mapped_column(String(20))  # mle|ai4s|swe_newgrad|career_switch
    target_level: Mapped[str] = mapped_column(String(10))  # junior|mid|senior
    timeline_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_hours: Mapped[int] = mapped_column(Integer)
    preferred_lang: Mapped[str] = mapped_column(String(20), default="python")
    platform: Mapped[str] = mapped_column(String(20), default="leetcode_cn")
    include_primers: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track: Mapped[str] = mapped_column(String(10), default="algo")  # algo|ml
    lc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    difficulty: Mapped[str] = mapped_column(String(10))  # easy|medium|hard
    patterns: Mapped[list] = mapped_column(JSON, default=list)
    importance: Mapped[int] = mapped_column(Integer, default=2)  # 1-4, 4=必会
    statement: Mapped[str | None] = mapped_column(Text, nullable=True)  # ml track only
    test_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # ml track only


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # null while in progress; ac_first_try|ac|failed|abandoned once finished
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hint_level_max: Mapped[int] = mapped_column(Integer, default=0)  # 0-4
    judge_failures: Mapped[int] = mapped_column(Integer, default=0)
    code_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    self_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    mistake_tags: Mapped[list] = mapped_column(JSON, default=list)
    review_feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    problem: Mapped[Problem] = relationship()
    hint_events: Mapped[list["HintEvent"]] = relationship(back_populates="attempt")


class HintEvent(Base):
    __tablename__ = "hint_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"), index=True)
    level: Mapped[int] = mapped_column(Integer)  # 1-4
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    attempt: Mapped[Attempt] = relationship(back_populates="hint_events")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    due_date: Mapped[date] = mapped_column(Date)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    # learning|reviewing|mastered
    mastery: Mapped[str] = mapped_column(String(12), default="learning")
    teach_back_passed: Mapped[bool] = mapped_column(Boolean, default=False)

    problem: Mapped[Problem] = relationship()


class MockSession(Base):
    __tablename__ = "mock_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"))
    mode: Mapped[str] = mapped_column(String(12), default="coding")  # coding|ml_coding
    transcript: Mapped[list] = mapped_column(JSON, default=list)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rubric: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    postmortem: Mapped[str | None] = mapped_column(Text, nullable=True)
    drills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    content_md: Mapped[str] = mapped_column(Text)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
