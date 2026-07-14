from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.config import settings
from app.db import get_db
from app.models import Attempt, Problem, Review, User
from app.schemas import PlanNewItem, PlanReviewItem, ProblemOut, TodayPlanOut
from app.services.planner import DueReview, NewCandidate, build_today_plan
from app.services.tracks import ml_unlocked

router = APIRouter(prefix="/api")

PLATFORM_HOST = {"leetcode_cn": "leetcode.cn", "leetcode_com": "leetcode.com"}


def problem_url(problem: Problem, user: User) -> str:
    if problem.track == "ml":
        return ""  # ML problems live inside the coach — no external page
    return f"https://{PLATFORM_HOST[user.platform]}/problems/{problem.slug}/"


def utc_today() -> date:
    """Attempt timestamps are stored in UTC — streak/heatmap math must use UTC
    days too, or evenings west of Greenwich count toward the wrong day."""
    return datetime.now(UTC).date()


def compute_streak(db: Session, user_id: int, today: date) -> int:
    rows = db.scalars(
        select(Attempt.created_at).where(
            Attempt.user_id == user_id, Attempt.outcome.is_not(None)
        )
    )
    days = {r.date() for r in rows}
    streak = 0
    day = today if today in days else today - timedelta(days=1)
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


@router.get("/plan/today", response_model=TodayPlanOut)
def today_plan(
    db: Session = Depends(get_db), user: User = Depends(require_user)
) -> TodayPlanOut:
    today = date.today()

    reviews = {r.problem_id: r for r in db.scalars(select(Review).where(Review.user_id == user.id))}
    due = [
        DueReview(
            problem_id=r.problem_id,
            importance=r.problem.importance,
            overdue_days=(today - r.due_date).days,
            ease_factor=r.ease_factor,
            review_count=r.review_count,
        )
        for r in reviews.values()
        if r.due_date <= today
    ]

    # candidates: never AC'd and not yet in the review loop
    solved_ids = {
        row for row in db.scalars(
            select(Attempt.problem_id).where(
                Attempt.user_id == user.id, Attempt.outcome.in_(["ac", "ac_first_try"])
            )
        )
    }
    candidates: list[NewCandidate] = []
    ml_candidates: list[NewCandidate] = []
    algo_total = algo_solved = 0
    for p in db.scalars(select(Problem)):
        is_primer = "primers" in p.patterns
        if p.track == "algo" and not is_primer:
            algo_total += 1
            if p.id in solved_ids:
                algo_solved += 1
        if p.id in solved_ids or p.id in reviews:
            continue
        candidate = NewCandidate(
            problem_id=p.id,
            patterns=p.patterns,
            difficulty=p.difficulty,
            importance=p.importance,
            is_primer=is_primer,
        )
        if p.track == "ml":
            ml_candidates.append(candidate)
        else:
            candidates.append(candidate)

    # mastery == learning, untouched for 3+ days -> resurface ahead of brand-new (§9.4.4)
    stale_cutoff = datetime.now() - timedelta(days=3)
    for r in reviews.values():
        if r.mastery != "learning" or r.due_date <= today:
            continue
        last_touch = db.scalar(
            select(func.max(Attempt.created_at)).where(
                Attempt.user_id == user.id, Attempt.problem_id == r.problem_id
            )
        )
        if last_touch is not None and last_touch < stale_cutoff:
            p = r.problem
            candidates.append(
                NewCandidate(
                    problem_id=p.id,
                    patterns=p.patterns,
                    difficulty=p.difficulty,
                    importance=p.importance,
                    is_stale_learning=True,
                )
            )

    from app.routers.stats import weakness_profile  # local import to avoid a cycle

    plan = build_today_plan(
        user.weekly_hours,
        user.include_primers,
        due,
        candidates,
        weak_patterns=weakness_profile(db, user.id, today).weak_patterns,
        weakness_weight=settings.weakness_weight,
        track=user.target_track,
        ml_candidates=ml_candidates,
        ml_unlocked=ml_unlocked(user.target_track, algo_solved, algo_total),
    )

    problems = {p.id: p for p in db.scalars(select(Problem))}
    cand_by_id = {c.problem_id: c for c in candidates}
    return TodayPlanOut(
        reviews=[
            PlanReviewItem(
                problem=ProblemOut.model_validate(problems[pid]),
                url=problem_url(problems[pid], user),
                due_date=reviews[pid].due_date,
                overdue_days=(today - reviews[pid].due_date).days,
                review_count=reviews[pid].review_count,
                mastery=reviews[pid].mastery,
            )
            for pid in plan.review_ids
        ],
        new=[
            PlanNewItem(
                problem=ProblemOut.model_validate(problems[pid]),
                url=problem_url(problems[pid], user),
                is_primer=cand_by_id[pid].is_primer,
                is_stale_learning=cand_by_id[pid].is_stale_learning,
            )
            for pid in plan.new_ids
        ],
        budget_minutes=plan.budget_minutes,
        streak=compute_streak(db, user.id, utc_today()),
    )
