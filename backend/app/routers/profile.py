from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import current_user_opt
from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api")


@router.post("/profile", response_model=ProfileOut)
def upsert_profile(
    body: ProfileIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(current_user_opt),
) -> User:
    if user is None:
        if settings.auth_enabled:
            raise HTTPException(401, "auth_required")
        user = User(**body.model_dump(), onboarded=True)
        db.add(user)
    else:
        for k, v in body.model_dump().items():
            setattr(user, k, v)
        user.onboarded = True
    db.commit()
    db.refresh(user)
    return user


@router.get("/profile", response_model=ProfileOut)
def read_profile(user: User | None = Depends(current_user_opt)) -> User:
    if user is None:
        if settings.auth_enabled:
            raise HTTPException(401, "auth_required")
        raise HTTPException(404, "no profile yet — complete onboarding first")
    if not user.onboarded:
        raise HTTPException(404, "no profile yet — complete onboarding first")
    return user
