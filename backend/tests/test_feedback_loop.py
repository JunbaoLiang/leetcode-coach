"""M2 endpoints: review-code, confirm-tags, teachback, weaknesses, weekly report.

LLM calls are monkeypatched — these tests cover routing, persistence, and gates.
"""

import pytest

from app.models import Attempt, Problem, Review
from app.services import llm

PROFILE = {
    "name": "junbao",
    "background": "计算化学 PhD",
    "target_track": "mle",
    "target_level": "junior",
    "weekly_hours": 14,
    "platform": "leetcode_cn",
}

REVIEW_JSON = {
    "correctness_risks": ["未处理空数组"],
    "complexity": {"claimed": None, "actual": "O(n) time, O(n) space"},
    "style_issues": [],
    "optimal_comparison": "已是最优",
    "mistake_tags_suggested": ["edge_case_missed", "not_a_real_tag"],
}


def seed_problem(db_factory) -> None:
    with db_factory() as db:
        db.add(Problem(id=1, slug="two-sum", title="Two Sum", difficulty="easy",
                       patterns=["arrays_hashing"], importance=4, lc_id=1))
        db.commit()


def finished_attempt(client, db_factory, with_code: bool = True) -> int:
    client.post("/api/profile", json=PROFILE)
    seed_problem(db_factory)
    att = client.post("/api/attempts", json={"problem_id": 1}).json()
    client.patch(
        f"/api/attempts/{att['id']}",
        json={
            "outcome": "ac",
            "duration_sec": 600,
            "recall_self_report": 4,
            "code_snapshot": "def two_sum(): ..." if with_code else None,
        },
    )
    return att["id"]


@pytest.fixture()
def mock_structured(monkeypatch):
    """Patch llm.structured_completion to return a canned schema instance."""
    canned = {}

    async def fake(system, messages, schema, max_tokens=3000):
        return schema.model_validate(canned["value"])

    monkeypatch.setattr(llm, "structured_completion", fake)
    return canned


# --- review-code ------------------------------------------------------------


def test_review_code_persists_and_filters_tags(client, db_factory, mock_structured) -> None:
    attempt_id = finished_attempt(client, db_factory)
    mock_structured["value"] = REVIEW_JSON
    resp = client.post("/api/review-code", json={"attempt_id": attempt_id})
    assert resp.status_code == 200
    body = resp.json()
    # unknown tag filtered out, only vocabulary survives
    assert body["mistake_tags_suggested"] == ["edge_case_missed"]
    with db_factory() as db:
        stored = db.get(Attempt, attempt_id).review_feedback
        assert stored["complexity"]["actual"] == "O(n) time, O(n) space"


def test_review_code_requires_code(client, db_factory, mock_structured) -> None:
    attempt_id = finished_attempt(client, db_factory, with_code=False)
    assert client.post("/api/review-code", json={"attempt_id": attempt_id}).status_code == 422


def test_confirm_tags_merges_after_user_approval(client, db_factory) -> None:
    attempt_id = finished_attempt(client, db_factory)
    resp = client.post(
        f"/api/attempts/{attempt_id}/confirm-tags", json={"tags": ["edge_case_missed"]}
    )
    assert resp.status_code == 200
    with db_factory() as db:
        assert db.get(Attempt, attempt_id).mistake_tags == ["edge_case_missed"]


def test_confirm_tags_rejects_unknown(client, db_factory) -> None:
    attempt_id = finished_attempt(client, db_factory)
    resp = client.post(f"/api/attempts/{attempt_id}/confirm-tags", json={"tags": ["nope"]})
    assert resp.status_code == 422


# --- teachback ---------------------------------------------------------------


def test_teachback_pass_sets_flag_but_not_mastered_too_early(
    client, db_factory, mock_structured
) -> None:
    attempt_id = finished_attempt(client, db_factory)
    mock_structured["value"] = {"passed": True, "gaps": [], "follow_up_question": None}
    body = client.post(
        "/api/teachback",
        json={"attempt_id": attempt_id, "transcript": [{"role": "user", "content": "讲解…"}]},
    ).json()
    assert body["passed"] is True
    # review_count == 1 -> teach_back_passed recorded, mastery stays reviewing
    assert body["mastery"] == "reviewing"
    with db_factory() as db:
        review = db.query(Review).one()
        assert review.teach_back_passed is True
        assert review.mastery == "reviewing"


def test_teachback_pass_promotes_to_mastered_after_enough_reviews(
    client, db_factory, mock_structured
) -> None:
    attempt_id = finished_attempt(client, db_factory)
    with db_factory() as db:
        review = db.query(Review).one()
        review.review_count = 3
        review.mastery = "reviewing"
        db.commit()
    mock_structured["value"] = {"passed": True, "gaps": [], "follow_up_question": None}
    body = client.post(
        "/api/teachback",
        json={"attempt_id": attempt_id, "transcript": [{"role": "user", "content": "讲解…"}]},
    ).json()
    assert body["mastery"] == "mastered"


def test_teachback_fail_keeps_gate_closed(client, db_factory, mock_structured) -> None:
    attempt_id = finished_attempt(client, db_factory)
    mock_structured["value"] = {
        "passed": False,
        "gaps": ["复杂度说错"],
        "follow_up_question": "worst case 是什么?",
    }
    body = client.post(
        "/api/teachback",
        json={"attempt_id": attempt_id, "transcript": [{"role": "user", "content": "讲解…"}]},
    ).json()
    assert body["passed"] is False
    assert body["follow_up_question"]
    with db_factory() as db:
        assert db.query(Review).one().teach_back_passed is False


# --- weaknesses ----------------------------------------------------------------


def test_weaknesses_endpoint_aggregates(client, db_factory) -> None:
    attempt_id = finished_attempt(client, db_factory)
    client.post(f"/api/attempts/{attempt_id}/confirm-tags", json={"tags": ["off_by_one"]})
    body = client.get("/api/weaknesses").json()
    assert body["tags"][0]["tag"] == "off_by_one"
    assert body["patterns"][0]["pattern"] == "arrays_hashing"


# --- weekly report ---------------------------------------------------------------


def test_weekly_report_computes_metrics_and_stores(client, db_factory, monkeypatch) -> None:
    finished_attempt(client, db_factory)

    async def fake_completion(system, messages, max_tokens=3000):
        assert '"attempts": 1' in system  # metrics injected into the prompt
        return "# 本周训练周报\n\n干得不错。"

    monkeypatch.setattr(llm, "completion", fake_completion)
    body = client.post("/api/reports/weekly").json()
    assert body["content_md"].startswith("# 本周训练周报")
    assert body["metrics"]["this_week"]["attempts"] == 1
    assert client.get("/api/reports").json()[0]["id"] == body["id"]
    assert client.get(f"/api/reports/{body['id']}").json()["content_md"] == body["content_md"]


def test_weekly_report_requires_activity(client, db_factory) -> None:
    client.post("/api/profile", json=PROFILE)
    assert client.post("/api/reports/weekly").status_code == 422
