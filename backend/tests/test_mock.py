"""M3 mock interview endpoints. LLM calls are monkeypatched."""

import pytest

from app.models import MockSession, Problem
from app.services import llm

PROFILE = {
    "name": "junbao",
    "background": "计算化学 PhD",
    "target_track": "mle",
    "target_level": "junior",
    "weekly_hours": 14,
}

EVALUATION = {
    "rubric": {
        "communication": 3,
        "problem_solving": 4,
        "code_correctness": 3,
        "complexity_analysis": 2,
        "edge_cases": 3,
        "time_management": 4,
    },
    "verdict": "lean_hire",
    "postmortem": "复杂度分析是最大短板(见第 2 轮)。",
    "drills": [{"pattern": "two_pointers", "count": 3, "instruction": "先说循环不变量"}],
}


def seed(client, db_factory) -> None:
    client.post("/api/profile", json=PROFILE)
    with db_factory() as db:
        db.add_all(
            [
                Problem(id=1, slug="3sum", title="3Sum", difficulty="medium",
                        patterns=["two_pointers"], importance=4, lc_id=15),
                Problem(id=2, slug="two-sum", title="Two Sum", difficulty="easy",
                        patterns=["arrays_hashing"], importance=4, lc_id=1),
            ]
        )
        db.commit()


@pytest.fixture()
def mock_llm(monkeypatch):
    async def fake_completion(system, messages, max_tokens=3000):
        assert "面试官" in system
        return "你好,今天我们做第 15 题,3Sum。请先讲思路。"

    async def fake_stream(system, messages, max_tokens=1500):
        for chunk in ["请继续", "说出你的思考。"]:
            yield chunk

    async def fake_structured(system, messages, schema, max_tokens=3000):
        assert "第1轮" in messages[0]["content"]  # numbered transcript reaches the grader
        return schema.model_validate(EVALUATION)

    monkeypatch.setattr(llm, "completion", fake_completion)
    monkeypatch.setattr(llm, "stream_completion", fake_stream)
    monkeypatch.setattr(llm, "structured_completion", fake_structured)


def start_session(client) -> dict:
    resp = client.post("/api/mock/start", json={"problem_id": 1})
    assert resp.status_code == 200
    return resp.json()


def test_start_with_chosen_problem(client, db_factory, mock_llm) -> None:
    seed(client, db_factory)
    body = start_session(client)
    assert body["problem"]["lc_id"] == 15
    assert "patterns" not in body["problem"]  # never spoil the pattern
    assert body["duration_sec"] == 45 * 60
    assert "3Sum" in body["opening"]
    with db_factory() as db:
        session = db.get(MockSession, body["session_id"])
        assert session.transcript[0]["role"] == "assistant"
        assert session.verdict is None


def test_random_pick_skips_easy_problems(client, db_factory, mock_llm) -> None:
    seed(client, db_factory)
    body = client.post("/api/mock/start", json={}).json()
    # only problem 1 (medium, importance 4) is interview-worthy; 2 is easy
    assert body["problem"]["id"] == 1


def test_message_streams_and_persists_transcript(client, db_factory, mock_llm) -> None:
    seed(client, db_factory)
    body = start_session(client)
    resp = client.post(
        "/api/mock/message",
        json={"session_id": body["session_id"], "message": "我想先用暴力解"},
    )
    assert resp.status_code == 200
    assert "[DONE]" in resp.text
    with db_factory() as db:
        transcript = db.get(MockSession, body["session_id"]).transcript
        assert [m["role"] for m in transcript] == ["assistant", "user", "assistant"]
        assert transcript[-1]["content"] == "请继续说出你的思考。"


def test_finish_grades_and_persists(client, db_factory, mock_llm) -> None:
    seed(client, db_factory)
    body = start_session(client)
    resp = client.post(
        "/api/mock/finish",
        json={
            "session_id": body["session_id"],
            "duration_sec": 1800,
            "code": "def three_sum(nums): ...",
        },
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["verdict"] == "lean_hire"
    assert result["rubric"]["complexity_analysis"] == 2
    assert result["drills"][0]["pattern"] == "two_pointers"
    # final code entered the transcript before grading
    assert any("最终提交的代码" in m["content"] for m in result["transcript"])

    # a finished session accepts no more messages / finishes
    again = client.post(
        "/api/mock/finish", json={"session_id": body["session_id"], "duration_sec": 1}
    )
    assert again.status_code == 409
    msg = client.post(
        "/api/mock/message", json={"session_id": body["session_id"], "message": "hi"}
    )
    assert msg.status_code == 409


def test_history_list_and_detail(client, db_factory, mock_llm) -> None:
    seed(client, db_factory)
    body = start_session(client)
    client.post(
        "/api/mock/finish", json={"session_id": body["session_id"], "duration_sec": 1800}
    )
    history = client.get("/api/mock").json()
    assert len(history) == 1
    assert history[0]["verdict"] == "lean_hire"
    assert history[0]["rubric_avg"] == pytest.approx(3.17, abs=0.01)
    detail = client.get(f"/api/mock/{body['session_id']}").json()
    assert detail["postmortem"].startswith("复杂度分析")
