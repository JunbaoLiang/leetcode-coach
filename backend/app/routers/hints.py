import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.models import Attempt, HintEvent, User
from app.schemas import HintIn
from app.services import llm

router = APIRouter(prefix="/api")


def weak_tags_for_patterns(db: Session, user: User, patterns: list[str]) -> list[str]:
    """Most common mistake tags from this user's history on overlapping patterns."""
    counts: dict[str, int] = {}
    attempts = db.scalars(
        select(Attempt).where(Attempt.user_id == user.id, Attempt.outcome.is_not(None))
    )
    for a in attempts:
        if not set(a.problem.patterns) & set(patterns):
            continue
        for tag in a.mistake_tags or []:
            counts[tag] = counts.get(tag, 0) + 1
    return [t for t, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:5]]


@router.post("/hints")
def request_hint(body: HintIn, db: Session = Depends(get_db)) -> StreamingResponse:
    attempt = db.get(Attempt, body.attempt_id)
    if attempt is None:
        raise HTTPException(404, "attempt not found")
    if attempt.outcome is not None:
        raise HTTPException(409, "attempt already finished")
    if body.level > attempt.hint_level_max + 1:
        raise HTTPException(
            422,
            f"hints escalate one level at a time (current L{attempt.hint_level_max}, "
            f"requested L{body.level})",
        )
    user = db.get(User, attempt.user_id)
    problem = attempt.problem

    system = llm.load_prompt(
        "coach",
        problem_title=problem.title,
        difficulty=problem.difficulty,
        patterns=", ".join(problem.patterns),
        background=user.background or "(未填写)",
        target_track=user.target_track,
        target_level=user.target_level,
        preferred_lang=user.preferred_lang,
        weak_tags=", ".join(weak_tags_for_patterns(db, user, problem.patterns)) or "(暂无)",
        level=body.level,
    )
    messages = [m.model_dump() for m in body.messages]
    if not messages or messages[-1]["role"] != "user":
        messages.append({"role": "user", "content": f"请给我 L{body.level} 级提示。"})

    attempt_id = attempt.id
    level = body.level

    async def event_stream() -> AsyncIterator[str]:
        chunks: list[str] = []
        try:
            async for text in llm.stream_completion(system, messages):
                chunks.append(text)
                yield f"data: {json.dumps({'text': text})}\n\n"
        except llm.LLMNotConfiguredError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return
        except Exception as e:  # surface a readable error instead of a dead socket
            yield f"data: {json.dumps({'error': f'LLM 调用失败: {e}'})}\n\n"
            return
        # persist the hint event only after a successful full stream
        with SessionLocal() as session:
            session.add(HintEvent(attempt_id=attempt_id, level=level, content="".join(chunks)))
            att = session.get(Attempt, attempt_id)
            att.hint_level_max = max(att.hint_level_max, level)
            session.commit()
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
