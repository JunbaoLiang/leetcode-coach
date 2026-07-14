from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import get_db
from app.models import Attempt, Problem, User
from app.routers.plan import compute_streak, utc_today
from app.schemas import (
    DifficultyProgress,
    PatternProgress,
    PatternStatOut,
    StatsOut,
    TagStatOut,
    WeaknessOut,
)
from app.services.planner import PATTERN_ORDER
from app.services.weakness import AttemptEvidence, aggregate_weaknesses

router = APIRouter(prefix="/api")

HEATMAP_WEEKS = 26


def weakness_profile(db: Session, user_id: int, today: date):
    finished = db.scalars(
        select(Attempt).where(Attempt.user_id == user_id, Attempt.outcome.is_not(None))
    )
    return aggregate_weaknesses(
        [
            AttemptEvidence(
                outcome=a.outcome,
                mistake_tags=a.mistake_tags or [],
                patterns=a.problem.patterns,
                when=a.created_at.date(),
            )
            for a in finished
        ],
        today,
    )


@router.get("/weaknesses", response_model=WeaknessOut)
def weaknesses(
    db: Session = Depends(get_db), user: User = Depends(require_user)
) -> WeaknessOut:
    profile = weakness_profile(db, user.id, date.today())
    return WeaknessOut(
        tags=[
            TagStatOut(tag=t.tag, count=t.count, weighted=round(t.weighted, 2), rate=t.rate)
            for t in profile.tags
        ],
        patterns=[
            PatternStatOut(pattern=p.pattern, attempts=p.attempts, error_rate=p.error_rate)
            for p in profile.patterns
        ],
        weak_patterns=profile.weak_patterns,
    )


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db), user: User = Depends(require_user)) -> StatsOut:
    today = utc_today()  # attempt timestamps are UTC — keep day math consistent

    problems = list(db.scalars(select(Problem).where(Problem.track == "algo")))
    finished = list(
        db.scalars(
            select(Attempt).where(Attempt.user_id == user.id, Attempt.outcome.is_not(None))
        )
    )
    solved_ids = {a.problem_id for a in finished if a.outcome in ("ac", "ac_first_try")}

    # pattern progress rings (primers excluded — they are a warmup, not a pattern)
    pattern_progress = []
    for pattern in PATTERN_ORDER:
        in_pattern = [p for p in problems if pattern in p.patterns and "primers" not in p.patterns]
        if not in_pattern:
            continue
        pattern_progress.append(
            PatternProgress(
                pattern=pattern,
                solved=sum(1 for p in in_pattern if p.id in solved_ids),
                total=len(in_pattern),
            )
        )

    difficulty_progress = []
    for diff in ("easy", "medium", "hard"):
        in_diff = [p for p in problems if p.difficulty == diff and "primers" not in p.patterns]
        difficulty_progress.append(
            DifficultyProgress(
                difficulty=diff,
                solved=sum(1 for p in in_diff if p.id in solved_ids),
                total=len(in_diff),
            )
        )

    # GitHub-style activity heatmap
    start = today - timedelta(weeks=HEATMAP_WEEKS)
    heatmap: dict[str, int] = {}
    for a in finished:
        day = a.created_at.date()
        if day >= start:
            heatmap[day.isoformat()] = heatmap.get(day.isoformat(), 0) + 1

    first_try = [a for a in finished if a.outcome == "ac_first_try"]
    recent = [a for a in finished if a.created_at.date() >= today - timedelta(days=30)]
    return StatsOut(
        pattern_progress=pattern_progress,
        difficulty_progress=difficulty_progress,
        streak=compute_streak(db, user.id, today),
        heatmap=heatmap,
        total_solved=len(solved_ids),
        total_attempts=len(finished),
        ac_first_try_rate=round(len(first_try) / len(finished), 3) if finished else None,
        avg_hint_level_30d=(
            round(sum(a.hint_level_max for a in recent) / len(recent), 2) if recent else None
        ),
    )
