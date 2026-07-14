"""Session auth (M5): HMAC-signed cookie sessions + GitHub OAuth helpers.

With ``AUTH_ENABLED=false`` (local dev default) everything falls back to the
original single-user behavior — no login, first user row is "the" user.
"""

import hmac
import time
from hashlib import sha256

import httpx
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

SESSION_COOKIE = "coach_session"
STATE_COOKIE = "oauth_state"
SESSION_MAX_AGE = 30 * 86400  # 30 days


def _sig(payload: str) -> str:
    return hmac.new(settings.session_secret.encode(), payload.encode(), sha256).hexdigest()


def sign_session(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time())}"
    return f"{payload}.{_sig(payload)}"


def verify_session(token: str) -> int | None:
    try:
        user_id, issued_at, sig = token.split(".")
        payload = f"{user_id}.{issued_at}"
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sig(payload)):
        return None
    if time.time() - int(issued_at) > SESSION_MAX_AGE:
        return None
    return int(user_id)


def current_user_opt(request: Request, db: Session = Depends(get_db)) -> User | None:
    """The logged-in user, or the single dev user when auth is off; None otherwise."""
    if not settings.auth_enabled:
        return db.scalar(select(User).order_by(User.id).limit(1))
    token = request.cookies.get(SESSION_COOKIE, "")
    user_id = verify_session(token) if token else None
    return db.get(User, user_id) if user_id else None


def require_user(user: User | None = Depends(current_user_opt)) -> User:
    if user is None:
        if settings.auth_enabled:
            raise HTTPException(401, "auth_required")
        raise HTTPException(404, "no profile yet — complete onboarding first")
    return user


def ensure_owner(resource_user_id: int, user: User) -> None:
    """Hide other users' resources as 404 rather than confirming they exist."""
    if resource_user_id != user.id:
        raise HTTPException(404, "not found")


def fetch_github_user(code: str) -> dict:
    """Exchange the OAuth code and return GitHub's /user payload.
    Separate function so tests can monkeypatch it."""
    token_resp = httpx.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    token_resp.raise_for_status()
    payload = token_resp.json()
    access_token = payload.get("access_token")
    if not access_token:
        # surface GitHub's reason: bad_verification_code = 授权码过期/已被使用(重新登录即可);
        # incorrect_client_credentials = GITHUB_CLIENT_SECRET 配置错误
        reason = payload.get("error", "unknown_error")
        raise HTTPException(502, f"GitHub token exchange failed: {reason}")
    user_resp = httpx.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    user_resp.raise_for_status()
    return user_resp.json()
