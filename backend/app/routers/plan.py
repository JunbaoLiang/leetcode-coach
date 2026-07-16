from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.config import settings
from app.db import get_db
from app.models import Attempt, DailyPlan, Problem, Review, User
from app.schemas import PlanItemOut, ProblemOut, TodayPlanOut
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


def _collect_candidates(
    db: Session, user: User, today: date, exclude: set[int] | None = None
) -> tuple[list[DueReview], list[NewCandidate], list[NewCandidate], bool]:
    """Due reviews + new-problem candidates (algo/ml split) for the planner."""
    exclude = exclude or set()
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
        if r.due_date <= today and r.problem_id not in exclude
    ]

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
        if p.id in solved_ids or p.id in reviews or p.id in exclude:
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
    stale_cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=3)
    for r in reviews.values():
        if r.mastery != "learning" or r.due_date <= today or r.problem_id in exclude:
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
    return due, candidates, ml_candidates, ml_unlocked(user.target_track, algo_solved, algo_total)


def _generate_items(db: Session, user: User, today: date) -> list[dict]:
    from app.routers.stats import weakness_profile  # local import to avoid a cycle

    due, candidates, ml_candidates, unlocked = _collect_candidates(db, user, today)
    plan = build_today_plan(
        user.weekly_hours,
        user.include_primers,
        due,
        candidates,
        weak_patterns=weakness_profile(db, user.id, today).weak_patterns,
        weakness_weight=settings.weakness_weight,
        track=user.target_track,
        ml_candidates=ml_candidates,
        ml_unlocked=unlocked,
    )
    stale_ids = {c.problem_id for c in candidates if c.is_stale_learning}
    items = [{"problem_id": pid, "kind": "review"} for pid in plan.review_ids]
    for pid in plan.new_ids:
        entry = {"problem_id": pid, "kind": "new"}
        if pid in stale_ids:
            entry["stale"] = True
        items.append(entry)
    return items


def _get_or_create_plan(db: Session, user: User, today: date) -> DailyPlan:
    snapshot = db.scalar(
        select(DailyPlan).where(DailyPlan.user_id == user.id, DailyPlan.plan_date == today)
    )
    if snapshot is None:
        snapshot = DailyPlan(
            user_id=user.id, plan_date=today, items=_generate_items(db, user, today)
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
    return snapshot


def _finished_today(db: Session, user_id: int, today: date) -> set[int]:
    rows = db.scalars(
        select(Attempt).where(Attempt.user_id == user_id, Attempt.outcome.is_not(None))
    )
    return {a.problem_id for a in rows if a.created_at.date() == today}


def _item_out(
    entry: dict, problems: dict[int, Problem], reviews: dict[int, Review], user: User, today: date,
    done: bool,
) -> PlanItemOut:
    problem = problems[entry["problem_id"]]
    review = reviews.get(problem.id) if entry["kind"] == "review" else None
    return PlanItemOut(
        problem=ProblemOut.model_validate(problem),
        url=problem_url(problem, user),
        kind=entry["kind"],
        done=done,
        stale=bool(entry.get("stale")),
        due_date=review.due_date if review else None,
        overdue_days=(today - review.due_date).days if review else None,
        review_count=review.review_count if review else None,
        mastery=review.mastery if review else None,
    )


@router.get("/plan/today", response_model=TodayPlanOut)
def today_plan(
    db: Session = Depends(get_db), user: User = Depends(require_user)
) -> TodayPlanOut:
    today = utc_today()
    snapshot = _get_or_create_plan(db, user, today)
    finished = _finished_today(db, user.id, today)

    problems = {p.id: p for p in db.scalars(select(Problem))}
    reviews = {r.problem_id: r for r in db.scalars(select(Review).where(Review.user_id == user.id))}

    items = [
        _item_out(entry, problems, reviews, user, today, entry["problem_id"] in finished)
        for entry in snapshot.items
        if entry["problem_id"] in problems
    ]
    # anything finished today outside the plan shows up as a completed bonus
    planned_ids = {entry["problem_id"] for entry in snapshot.items}
    for pid in sorted(finished - planned_ids):
        if pid in problems:
            extra = {"problem_id": pid, "kind": "bonus"}
            items.append(_item_out(extra, problems, reviews, user, today, True))

    planned = [i for i in items if i.kind != "bonus"]
    return TodayPlanOut(
        items=items,
        done_count=sum(1 for i in planned if i.done),
        total_count=len(planned),
        bonus_done=sum(1 for i in items if i.kind == "bonus" and i.done),
        budget_minutes=round(user.weekly_hours * 60 / 7),
        streak=compute_streak(db, user.id, today),
    )


@router.post("/plan/bonus", response_model=PlanItemOut)
def add_bonus(db: Session = Depends(get_db), user: User = Depends(require_user)) -> PlanItemOut:
    """加餐 — hand out one more problem beyond today's plan (weakness-biased)."""
    from app.routers.stats import weakness_profile

    today = utc_today()
    snapshot = _get_or_create_plan(db, user, today)
    planned_ids = {entry["problem_id"] for entry in snapshot.items}

    _, candidates, ml_candidates, unlocked = _collect_candidates(
        db, user, today, exclude=planned_ids
    )
    plan = build_today_plan(
        user.weekly_hours,
        user.include_primers,
        [],
        candidates,
        weak_patterns=weakness_profile(db, user.id, today).weak_patterns,
        weakness_weight=settings.weakness_weight,
        track=user.target_track,
        ml_candidates=ml_candidates,
        ml_unlocked=unlocked,
    )
    if not plan.new_ids:
        raise HTTPException(404, "题库里没有可加餐的题了——你也太能刷了")
    pid = plan.new_ids[0]

    snapshot.items = [*snapshot.items, {"problem_id": pid, "kind": "bonus"}]
    db.commit()

    problems = {p.id: p for p in db.scalars(select(Problem).where(Problem.id == pid))}
    return _item_out({"problem_id": pid, "kind": "bonus"}, problems, {}, user, today, False)
