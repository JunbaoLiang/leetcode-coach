from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ensure_owner, require_user
from app.db import get_db
from app.models import Attempt, Review, User
from app.schemas import TeachbackIn, TeachbackOut, TeachbackResult
from app.services import llm

router = APIRouter(prefix="/api")


@router.post("/teachback", response_model=TeachbackResult)
async def teachback(
    body: TeachbackIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_user),
) -> TeachbackResult:
    attempt = db.get(Attempt, body.attempt_id)
    if attempt is None:
        raise HTTPException(404, "attempt not found")
    ensure_owner(attempt.user_id, current)
    if attempt.outcome is None:
        raise HTTPException(409, "attempt not finished yet")
    problem = attempt.problem
    if "primers" in problem.patterns:
        raise HTTPException(422, "primers skip teach-back (AC 即通过)")

    user = db.get(User, attempt.user_id)
    system = llm.load_prompt(
        "teachback",
        problem_title=problem.title,
        difficulty=problem.difficulty,
        patterns=", ".join(problem.patterns),
        background=user.background or "(未填写)",
    )
    messages = [m.model_dump() for m in body.transcript]
    try:
        verdict = await llm.structured_completion(system, messages, TeachbackOut)
    except llm.LLMNotConfiguredError as e:
        raise HTTPException(503, str(e)) from e
    except llm.LLMOutputError as e:
        raise HTTPException(502, str(e)) from e

    mastery = None
    review = db.scalar(
        select(Review).where(
            Review.user_id == attempt.user_id, Review.problem_id == problem.id
        )
    )
    if review is not None:
        if verdict.passed:
            review.teach_back_passed = True
            # §8.4 gate — teach-back is the last door to 'mastered'
            if review.review_count >= 3 and review.mastery != "learning":
                review.mastery = "mastered"
            db.commit()
        mastery = review.mastery
    return TeachbackResult(**verdict.model_dump(), mastery=mastery)
