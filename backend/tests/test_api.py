from datetime import date

from app.models import Problem

PROFILE = {
    "name": "junbao",
    "background": "计算化学 PhD",
    "target_track": "mle",
    "target_level": "junior",
    "weekly_hours": 14,
    "platform": "leetcode_cn",
    "include_primers": False,
}


def seed_problems(db_factory) -> None:
    with db_factory() as db:
        db.add_all(
            [
                Problem(id=1, slug="two-sum", title="Two Sum", difficulty="easy",
                        patterns=["arrays_hashing"], importance=4, lc_id=1),
                Problem(id=2, slug="3sum", title="3Sum", difficulty="medium",
                        patterns=["two_pointers"], importance=4, lc_id=15),
                Problem(id=3, slug="add-two-integers", title="Add Two Integers",
                        difficulty="easy", patterns=["primers", "math"], importance=1,
                        lc_id=2235),
            ]
        )
        db.commit()


def test_profile_roundtrip(client) -> None:
    assert client.get("/api/profile").status_code == 404
    resp = client.post("/api/profile", json=PROFILE)
    assert resp.status_code == 200
    got = client.get("/api/profile").json()
    assert got["target_track"] == "mle"
    assert got["weekly_hours"] == 14


def test_plan_requires_profile(client) -> None:
    assert client.get("/api/plan/today").status_code == 404


def test_full_practice_flow(client, db_factory) -> None:
    client.post("/api/profile", json=PROFILE)
    seed_problems(db_factory)

    # plan: pattern order puts two-sum before 3sum; primer excluded (include_primers=False)
    plan = client.get("/api/plan/today").json()
    item_ids = [item["problem"]["id"] for item in plan["items"]]
    assert item_ids[0] == 1
    assert 3 not in item_ids
    assert plan["items"][0]["kind"] == "new"
    assert plan["items"][0]["url"] == "https://leetcode.cn/problems/two-sum/"
    assert plan["done_count"] == 0

    # start + reload reuses the same in-progress attempt
    a1 = client.post("/api/attempts", json={"problem_id": 1}).json()
    a2 = client.post("/api/attempts", json={"problem_id": 1}).json()
    assert a1["id"] == a2["id"]

    # finish -> review row scheduled into the future
    resp = client.patch(
        f"/api/attempts/{a1['id']}",
        json={
            "outcome": "ac_first_try",
            "duration_sec": 900,
            "recall_self_report": 4,
            "mistake_tags": ["edge_case_missed"],
            "code_snapshot": "def two_sum(): ...",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quality"] == 4.5
    assert body["review"]["review_count"] == 1
    assert date.fromisoformat(body["review"]["due_date"]) > date.today()

    # the checklist is frozen: the solved problem STAYS on it, checked off
    plan2 = client.get("/api/plan/today").json()
    solved_item = next(i for i in plan2["items"] if i["problem"]["id"] == 1)
    assert solved_item["done"] is True
    assert plan2["done_count"] == 1
    assert [i["problem"]["id"] for i in plan2["items"]] == [
        i["problem"]["id"] for i in plan["items"]
    ]  # same list as this morning

    # stats aggregate
    stats = client.get("/api/stats").json()
    assert stats["total_solved"] == 1
    assert stats["streak"] == 1
    assert stats["ac_first_try_rate"] == 1.0
    ah = {p["pattern"]: p for p in stats["pattern_progress"]}["arrays_hashing"]
    assert (ah["solved"], ah["total"]) == (1, 1)


def test_primer_skips_review_scheduling(client, db_factory) -> None:
    client.post("/api/profile", json={**PROFILE, "include_primers": True})
    seed_problems(db_factory)

    plan = client.get("/api/plan/today").json()
    assert [item["problem"]["id"] for item in plan["items"]][0] == 3  # primer first

    att = client.post("/api/attempts", json={"problem_id": 3}).json()
    body = client.patch(
        f"/api/attempts/{att['id']}",
        json={"outcome": "ac", "duration_sec": 300, "recall_self_report": 5},
    ).json()
    assert body["review"] is None  # primers never enter SM-2


def test_finish_rejects_unknown_mistake_tags(client, db_factory) -> None:
    client.post("/api/profile", json=PROFILE)
    seed_problems(db_factory)
    att = client.post("/api/attempts", json={"problem_id": 1}).json()
    resp = client.patch(
        f"/api/attempts/{att['id']}",
        json={
            "outcome": "ac",
            "duration_sec": 60,
            "recall_self_report": 3,
            "mistake_tags": ["made_it_up"],
        },
    )
    assert resp.status_code == 422


def test_hint_level_must_escalate_one_at_a_time(client, db_factory) -> None:
    client.post("/api/profile", json=PROFILE)
    seed_problems(db_factory)
    att = client.post("/api/attempts", json={"problem_id": 1}).json()
    resp = client.post(
        "/api/hints", json={"attempt_id": att["id"], "level": 2, "messages": []}
    )
    assert resp.status_code == 422


def test_finish_heals_duplicate_in_progress_attempts(client, db_factory) -> None:
    client.post("/api/profile", json=PROFILE)
    seed_problems(db_factory)
    from app.models import Attempt

    a1 = client.post("/api/attempts", json={"problem_id": 1}).json()
    # simulate a double-fired start that slipped past the client-side dedupe
    with db_factory() as db:
        db.add(Attempt(user_id=1, problem_id=1))
        db.commit()
    client.patch(
        f"/api/attempts/{a1['id']}",
        json={"outcome": "ac", "duration_sec": 60, "recall_self_report": 4},
    )
    with db_factory() as db:
        rows = db.query(Attempt).filter(Attempt.problem_id == 1).all()
        assert len(rows) == 1
        assert rows[0].outcome == "ac"


def test_failed_attempt_resets_to_learning_and_due_tomorrow(client, db_factory) -> None:
    client.post("/api/profile", json=PROFILE)
    seed_problems(db_factory)
    att = client.post("/api/attempts", json={"problem_id": 2}).json()
    body = client.patch(
        f"/api/attempts/{att['id']}",
        json={
            "outcome": "failed",
            "duration_sec": 2400,
            "recall_self_report": 1,
            "mistake_tags": ["pattern_not_recognized"],
        },
    ).json()
    assert body["review"]["mastery"] == "learning"
    assert body["review"]["interval_days"] == 1
