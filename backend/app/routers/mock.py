import json
import random
from collections.abc import AsyncIterator
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import ensure_owner, require_user
from app.db import SessionLocal, get_db
from app.models import MockSession, Problem, User
from app.routers.stats import weakness_profile
from app.schemas import (
    MOCK_DURATION_SEC,
    MockEvaluation,
    MockFinishIn,
    MockMessageIn,
    MockProblemOut,
    MockSessionOut,
    MockSessionSummary,
    MockStartIn,
    MockStartOut,
)
from app.services import llm

router = APIRouter(prefix="/api")

KICKOFF_MESSAGE = "(候选人已就座,面试开始,请开场并出题。)"


def _interviewer_system(problem: Problem, user: User) -> str:
    return llm.load_prompt(
        "interviewer",
        lc_id=problem.lc_id or "",
        problem_title=problem.title,
        target_level=user.target_level,
        preferred_lang=user.preferred_lang,
    )


def _pick_problem(db: Session, user: User) -> Problem:
    """§12 M3 — random pick biased toward weak patterns; interview-worthy problems only."""
    problems = [
        p
        for p in db.scalars(select(Problem).where(Problem.track == "algo"))
        if "primers" not in p.patterns
        and p.difficulty in ("medium", "hard")
        and p.importance >= 3
    ]
    if not problems:
        raise HTTPException(409, "题库为空,先运行种子导入")
    weak = set(weakness_profile(db, user.id, date.today()).weak_patterns)
    if weak:
        biased = [p for p in problems if set(p.patterns) & weak]
        if biased:
            problems = biased
    return random.choice(problems)


def _get_open_session(db: Session, session_id: int) -> MockSession:
    session = db.get(MockSession, session_id)
    if session is None:
        raise HTTPException(404, "mock session not found")
    if session.verdict is not None:
        raise HTTPException(409, "这场面试已经结束了")
    return session


@router.post("/mock/start", response_model=MockStartOut)
async def start_mock(
    body: MockStartIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> MockStartOut:
    if body.problem_id is not None:
        problem = db.get(Problem, body.problem_id)
        if problem is None:
            raise HTTPException(404, "problem not found")
    else:
        problem = _pick_problem(db, user)

    system = _interviewer_system(problem, user)
    try:
        opening = await llm.completion(
            system, [{"role": "user", "content": KICKOFF_MESSAGE}], max_tokens=500
        )
    except llm.LLMNotConfiguredError as e:
        raise HTTPException(503, str(e)) from e

    session = MockSession(
        user_id=user.id,
        problem_id=problem.id,
        mode="coding",
        transcript=[{"role": "assistant", "content": opening}],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return MockStartOut(
        session_id=session.id,
        problem=MockProblemOut.model_validate(problem),
        opening=opening,
        duration_sec=MOCK_DURATION_SEC,
    )


@router.post("/mock/message")
def mock_message(
    body: MockMessageIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_user),
) -> StreamingResponse:
    session = _get_open_session(db, body.session_id)
    ensure_owner(session.user_id, current)
    user = db.get(User, session.user_id)
    problem = db.get(Problem, session.problem_id)

    transcript = [*session.transcript, {"role": "user", "content": body.message}]
    session.transcript = transcript
    db.commit()

    system = _interviewer_system(problem, user)
    session_id = session.id

    async def event_stream() -> AsyncIterator[str]:
        chunks: list[str] = []
        try:
            async for text in llm.stream_completion(system, transcript, max_tokens=600):
                chunks.append(text)
                yield f"data: {json.dumps({'text': text})}\n\n"
        except llm.LLMNotConfiguredError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return
        except Exception as e:
            yield f"data: {json.dumps({'error': llm.friendly_llm_error(e)})}\n\n"
            return
        with SessionLocal() as fresh:
            mock = fresh.get(MockSession, session_id)
            mock.transcript = [*mock.transcript, {"role": "assistant", "content": "".join(chunks)}]
            fresh.commit()
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _numbered_transcript(transcript: list[dict]) -> str:
    lines = []
    for i, msg in enumerate(transcript, start=1):
        speaker = "面试官" if msg["role"] == "assistant" else "候选人"
        lines.append(f"第{i}轮 [{speaker}]:\n{msg['content']}")
    return "\n\n".join(lines)


@router.post("/mock/finish", response_model=MockSessionOut)
async def finish_mock(
    body: MockFinishIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_user),
) -> MockSessionOut:
    session = _get_open_session(db, body.session_id)
    ensure_owner(session.user_id, current)
    user = db.get(User, session.user_id)
    problem = db.get(Problem, session.problem_id)

    transcript = list(session.transcript)
    if body.code and body.code.strip():
        transcript.append(
            {"role": "user", "content": f"[候选人最终提交的代码]\n```\n{body.code}\n```"}
        )

    system = llm.load_prompt(
        "interviewer_finish",
        lc_id=problem.lc_id or "",
        problem_title=problem.title,
        difficulty=problem.difficulty,
        patterns=", ".join(problem.patterns),
        target_level=user.target_level,
        duration_min=round(body.duration_sec / 60),
    )
    grading_input = (
        f"以下是完整对话记录:\n\n{_numbered_transcript(transcript)}\n\n请给出评估 JSON。"
    )
    messages = [{"role": "user", "content": grading_input}]
    try:
        evaluation = await llm.structured_completion(system, messages, MockEvaluation)
    except llm.LLMNotConfiguredError as e:
        raise HTTPException(503, str(e)) from e
    except llm.LLMOutputError as e:
        raise HTTPException(502, str(e)) from e

    session.transcript = transcript
    session.duration_sec = body.duration_sec
    session.rubric = evaluation.rubric.model_dump()
    session.verdict = evaluation.verdict
    session.postmortem = evaluation.postmortem
    session.drills = [d.model_dump() for d in evaluation.drills]
    db.commit()
    db.refresh(session)
    return _session_out(session, problem)


def _session_out(session: MockSession, problem: Problem) -> MockSessionOut:
    return MockSessionOut(
        id=session.id,
        problem=MockProblemOut.model_validate(problem),
        transcript=session.transcript,
        duration_sec=session.duration_sec,
        rubric=session.rubric,
        verdict=session.verdict,
        postmortem=session.postmortem,
        drills=session.drills,
        created_at=session.created_at,
    )


@router.get("/mock", response_model=list[MockSessionSummary])
def list_mock_sessions(
    db: Session = Depends(get_db), user: User = Depends(require_user)
) -> list[MockSessionSummary]:
    sessions = db.scalars(
        select(MockSession).where(MockSession.user_id == user.id).order_by(MockSession.id.desc())
    )
    problems = {p.id: p for p in db.scalars(select(Problem))}
    out = []
    for s in sessions:
        avg = round(sum(s.rubric.values()) / len(s.rubric), 2) if s.rubric else None
        out.append(
            MockSessionSummary(
                id=s.id,
                problem=MockProblemOut.model_validate(problems[s.problem_id]),
                verdict=s.verdict,
                rubric_avg=avg,
                created_at=s.created_at,
            )
        )
    return out


@router.get("/mock/{session_id}", response_model=MockSessionOut)
def get_mock_session(
    session_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_user),
) -> MockSessionOut:
    session = db.get(MockSession, session_id)
    if session is None:
        raise HTTPException(404, "mock session not found")
    ensure_owner(session.user_id, current)
    problem = db.get(Problem, session.problem_id)
    return _session_out(session, problem)
