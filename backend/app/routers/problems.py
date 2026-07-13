from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Problem
from app.schemas import ProblemDetail, ProblemOut

router = APIRouter(prefix="/api")


@router.get("/problems/{problem_id}", response_model=ProblemDetail)
def get_problem(problem_id: int, db: Session = Depends(get_db)) -> Problem:
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(404, "problem not found")
    return problem


@router.get("/problems", response_model=list[ProblemOut])
def list_problems(
    pattern: str | None = None,
    difficulty: str | None = None,
    track: str | None = None,
    db: Session = Depends(get_db),
) -> list[Problem]:
    stmt = select(Problem).order_by(Problem.id)
    if difficulty:
        stmt = stmt.where(Problem.difficulty == difficulty)
    if track:
        stmt = stmt.where(Problem.track == track)
    problems = list(db.scalars(stmt))
    if pattern:
        problems = [p for p in problems if pattern in p.patterns]
    return problems
