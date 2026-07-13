from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api")


def get_current_user(db: Session) -> User | None:
    # single-user mode until M5 (no auth): the first row is "the" user
    return db.scalar(select(User).order_by(User.id).limit(1))


@router.post("/profile", response_model=ProfileOut)
def upsert_profile(body: ProfileIn, db: Session = Depends(get_db)) -> User:
    user = get_current_user(db)
    if user is None:
        user = User(**body.model_dump())
        db.add(user)
    else:
        for k, v in body.model_dump().items():
            setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.get("/profile", response_model=ProfileOut)
def read_profile(db: Session = Depends(get_db)) -> User:
    user = get_current_user(db)
    if user is None:
        raise HTTPException(404, "no profile yet — complete onboarding first")
    return user
