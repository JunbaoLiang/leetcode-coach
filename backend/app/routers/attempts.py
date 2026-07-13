import random
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ensure_owner, require_user
from app.db import get_db
from app.models import Attempt, Problem, Review, User
from app.schemas import (
    MISTAKE_TAGS,
    AttemptFinishIn,
    AttemptFinishOut,
    AttemptOut,
    AttemptStartIn,
    ReviewOut,
)
from app.services.scheduler import compute_quality, update_review

router = APIRouter(prefix="/api")


@router.post("/attempts", response_model=AttemptOut)
def start_attempt(
    body: AttemptStartIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Attempt:
    problem = db.get(Problem, body.problem_id)
    if problem is None:
        raise HTTPException(404, "problem not found")
    # reuse an unfinished attempt (page reload should not spawn duplicates)
    existing = db.scalar(
        select(Attempt).where(
            Attempt.user_id == user.id,
            Attempt.problem_id == problem.id,
            Attempt.outcome.is_(None),
        )
    )
    if existing is not None:
        return existing
    attempt = Attempt(user_id=user.id, problem_id=problem.id)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.patch("/attempts/{attempt_id}", response_model=AttemptFinishOut)
def finish_attempt(
    attempt_id: int,
    body: AttemptFinishIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> AttemptFinishOut:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(404, "attempt not found")
    ensure_owner(attempt.user_id, user)
    if attempt.outcome is not None:
        raise HTTPException(409, "attempt already finished")
    unknown = set(body.mistake_tags) - set(MISTAKE_TAGS)
    if unknown:
        raise HTTPException(422, f"unknown mistake tags: {sorted(unknown)}")

    attempt.outcome = body.outcome
    attempt.duration_sec = body.duration_sec
    attempt.mistake_tags = body.mistake_tags
    attempt.code_snapshot = body.code_snapshot
    attempt.self_explanation = body.self_explanation
    attempt.judge_failures = body.judge_failures

    problem = attempt.problem
    review_out = None
    quality = None
    if "primers" not in problem.patterns:  # primers skip spaced repetition (§11.4)
        quality = compute_quality(
            body.recall_self_report, attempt.hint_level_max, body.judge_failures, body.outcome
        )
        review = db.scalar(
            select(Review).where(
                Review.user_id == attempt.user_id, Review.problem_id == problem.id
            )
        )
        if review is None:
            review = Review(
                user_id=attempt.user_id,
                problem_id=problem.id,
                due_date=date.today(),
                ease_factor=2.5,
                interval_days=0,
                review_count=0,
            )
            db.add(review)
        state = update_review(
            review.ease_factor,
            review.interval_days,
            review.review_count,
            quality,
            problem.importance,
            date.today(),
            rng=random.Random(),
        )
        review.ease_factor = state.ease_factor
        review.interval_days = state.interval_days
        review.review_count = state.review_count
        review.due_date = state.due_date
        review.last_quality = quality
        if quality < 3:
            review.mastery = "learning"
        elif review.teach_back_passed and review.review_count >= 3:
            review.mastery = "mastered"
        else:
            review.mastery = "reviewing"
        db.flush()
        review_out = ReviewOut.model_validate(review)

    # heal duplicate in-progress attempts for the same problem (e.g. double-fired starts),
    # but never drop one that already carries hint events
    siblings = db.scalars(
        select(Attempt).where(
            Attempt.user_id == attempt.user_id,
            Attempt.problem_id == attempt.problem_id,
            Attempt.outcome.is_(None),
            Attempt.id != attempt.id,
        )
    )
    for sib in siblings:
        if not sib.hint_events:
            db.delete(sib)

    db.commit()
    db.refresh(attempt)
    return AttemptFinishOut(
        attempt=AttemptOut.model_validate(attempt), review=review_out, quality=quality
    )
