import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    STATE_COOKIE,
    fetch_github_user,
    sign_session,
)
from app.config import settings
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/api/auth")


def _redirect_uri(request: Request) -> str:
    base = settings.public_base_url.rstrip("/") or str(request.base_url).rstrip("/")
    return f"{base}/api/auth/callback"


@router.get("/github")
def github_login(request: Request) -> RedirectResponse:
    if not settings.auth_enabled:
        raise HTTPException(404, "auth is disabled")
    state = secrets.token_urlsafe(16)
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": _redirect_uri(request),
            "scope": "read:user",
            "state": state,
        }
    )
    resp = RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")
    resp.set_cookie(STATE_COOKIE, state, max_age=300, httponly=True, samesite="lax")
    return resp


@router.get("/callback")
def github_callback(
    request: Request, code: str = "", state: str = "", db: Session = Depends(get_db)
) -> RedirectResponse:
    if not settings.auth_enabled:
        raise HTTPException(404, "auth is disabled")
    if not code or not state or state != request.cookies.get(STATE_COOKIE):
        raise HTTPException(400, "OAuth state 校验失败,请重新登录")

    info = fetch_github_user(code)
    github_id = str(info["id"])
    user = db.scalar(select(User).where(User.github_id == github_id))
    if user is None:
        user = User(
            name=info.get("name") or info.get("login") or "github-user",
            github_id=github_id,
            avatar_url=info.get("avatar_url"),
            target_track="mle",
            target_level="junior",
            weekly_hours=8,
            onboarded=False,
        )
        db.add(user)
    else:
        user.avatar_url = info.get("avatar_url") or user.avatar_url
    db.commit()
    db.refresh(user)

    resp = RedirectResponse("/")
    resp.set_cookie(
        SESSION_COOKIE,
        sign_session(user.id),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    resp.delete_cookie(STATE_COOKIE)
    return resp


@router.post("/logout")
def logout() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE)
    return resp
