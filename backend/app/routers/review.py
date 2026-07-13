from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import ensure_owner, require_user
from app.db import get_db
from app.models import Attempt, User
from app.schemas import MISTAKE_TAGS, ConfirmTagsIn, ReviewCodeIn, ReviewCodeOut
from app.services import llm

router = APIRouter(prefix="/api")


@router.post("/review-code", response_model=ReviewCodeOut)
async def review_code(
    body: ReviewCodeIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_user),
) -> ReviewCodeOut:
    attempt = db.get(Attempt, body.attempt_id)
    if attempt is None:
        raise HTTPException(404, "attempt not found")
    ensure_owner(attempt.user_id, current)
    if attempt.outcome is None:
        raise HTTPException(409, "attempt not finished yet")
    if not attempt.code_snapshot:
        raise HTTPException(422, "attempt has no code snapshot to review")

    user = db.get(User, attempt.user_id)
    problem = attempt.problem
    system = llm.load_prompt(
        "reviewer",
        problem_title=problem.title,
        difficulty=problem.difficulty,
        patterns=", ".join(problem.patterns),
        preferred_lang=user.preferred_lang,
        background=user.background or "(未填写)",
    )
    messages = [
        {
            "role": "user",
            "content": f"请 review 这份 AC 代码:\n```{user.preferred_lang}\n"
            f"{attempt.code_snapshot}\n```",
        }
    ]
    try:
        result = await llm.structured_completion(system, messages, ReviewCodeOut)
    except llm.LLMNotConfiguredError as e:
        raise HTTPException(503, str(e)) from e
    except llm.LLMOutputError as e:
        raise HTTPException(502, str(e)) from e

    # only vocabulary tags survive; the user confirms them separately before they count
    result.mistake_tags_suggested = [
        t for t in result.mistake_tags_suggested if t in MISTAKE_TAGS
    ]
    attempt.review_feedback = result.model_dump()
    db.commit()
    return result


@router.post("/attempts/{attempt_id}/confirm-tags")
def confirm_tags(
    attempt_id: int,
    body: ConfirmTagsIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_user),
) -> dict:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(404, "attempt not found")
    ensure_owner(attempt.user_id, current)
    unknown = set(body.tags) - set(MISTAKE_TAGS)
    if unknown:
        raise HTTPException(422, f"unknown mistake tags: {sorted(unknown)}")
    merged = list(dict.fromkeys([*attempt.mistake_tags, *body.tags]))
    attempt.mistake_tags = merged
    db.commit()
    return {"mistake_tags": merged}
