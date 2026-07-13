"""M5: GitHub OAuth sessions + multi-user isolation. GitHub exchange is monkeypatched."""

import pytest

from app import auth as auth_module
from app.auth import sign_session
from app.config import settings
from app.models import Problem, User

GITHUB_ALICE = {"id": 111, "login": "alice", "name": "Alice", "avatar_url": "https://a.png"}
GITHUB_BOB = {"id": 222, "login": "bob", "name": None, "avatar_url": "https://b.png"}


@pytest.fixture()
def auth_on(monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "session_secret", "test-secret")
    monkeypatch.setattr(settings, "github_client_id", "cid")
    monkeypatch.setattr(settings, "github_client_secret", "csecret")


def login_via_github(client, monkeypatch, payload) -> None:
    monkeypatch.setattr(auth_module, "fetch_github_user", lambda code: payload)
    # routers.auth imported the name directly — patch both references
    from app.routers import auth as auth_router

    monkeypatch.setattr(auth_router, "fetch_github_user", lambda code: payload)
    start = client.get("/api/auth/github", follow_redirects=False)
    assert start.status_code == 307
    assert "github.com/login/oauth/authorize" in start.headers["location"]
    state = client.cookies.get("oauth_state")
    done = client.get(f"/api/auth/callback?code=x&state={state}", follow_redirects=False)
    assert done.status_code == 307
    assert client.cookies.get("coach_session")


def test_unauthenticated_requests_get_401(client, auth_on) -> None:
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/plan/today").status_code == 401
    assert client.get("/api/stats").status_code == 401


def test_oauth_flow_creates_user_and_session(client, db_factory, auth_on, monkeypatch) -> None:
    login_via_github(client, monkeypatch, GITHUB_ALICE)
    # new user exists but has not onboarded -> profile 404 drives the onboarding page
    assert client.get("/api/profile").status_code == 404
    resp = client.post(
        "/api/profile",
        json={"name": "Alice", "target_track": "mle", "target_level": "junior",
              "weekly_hours": 10},
    )
    assert resp.status_code == 200
    got = client.get("/api/profile").json()
    assert got["avatar_url"] == "https://a.png"
    with db_factory() as db:
        user = db.query(User).one()
        assert user.github_id == "111"
        assert user.onboarded is True


def test_callback_rejects_bad_state(client, auth_on, monkeypatch) -> None:
    monkeypatch.setattr(auth_module, "fetch_github_user", lambda code: GITHUB_ALICE)
    resp = client.get("/api/auth/callback?code=x&state=forged", follow_redirects=False)
    assert resp.status_code == 400


def test_logout_clears_session(client, db_factory, auth_on, monkeypatch) -> None:
    login_via_github(client, monkeypatch, GITHUB_ALICE)
    client.post("/api/auth/logout")
    assert client.get("/api/profile").status_code == 401


def test_users_cannot_touch_each_others_data(client, db_factory, auth_on) -> None:
    with db_factory() as db:
        db.add_all(
            [
                User(id=1, name="alice", github_id="111", target_track="mle",
                     target_level="junior", weekly_hours=10, onboarded=True),
                User(id=2, name="bob", github_id="222", target_track="mle",
                     target_level="junior", weekly_hours=10, onboarded=True),
                Problem(id=1, slug="two-sum", title="Two Sum", difficulty="easy",
                        patterns=["arrays_hashing"], importance=4, lc_id=1),
            ]
        )
        db.commit()

    client.cookies.set("coach_session", sign_session(1))  # alice
    attempt = client.post("/api/attempts", json={"problem_id": 1}).json()

    client.cookies.set("coach_session", sign_session(2))  # bob
    resp = client.patch(
        f"/api/attempts/{attempt['id']}",
        json={"outcome": "ac", "duration_sec": 60, "recall_self_report": 4},
    )
    assert resp.status_code == 404  # existence is hidden, not just forbidden

    # bob's stats see none of alice's activity
    stats = client.get("/api/stats").json()
    assert stats["total_attempts"] == 0


def test_tampered_session_cookie_is_rejected(client, auth_on) -> None:
    client.cookies.set("coach_session", "1.9999999999.deadbeef")
    assert client.get("/api/profile").status_code == 401


def test_dev_mode_stays_single_user(client, db_factory) -> None:
    # auth disabled (default): original single-user flow untouched
    resp = client.post(
        "/api/profile",
        json={"name": "junbao", "target_track": "mle", "target_level": "junior",
              "weekly_hours": 14},
    )
    assert resp.status_code == 200
    assert client.get("/api/profile").status_code == 200
    assert client.get("/api/auth/github").status_code == 404
