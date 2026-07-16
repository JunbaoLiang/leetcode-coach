"""Daily checklist semantics: frozen snapshot, checked-off items, bonus problems."""

from app.models import Problem

PROFILE = {
    "name": "junbao",
    "target_track": "mle",
    "target_level": "junior",
    "weekly_hours": 14,  # 120 min/day -> 3 new slots
}


def seed(client, db_factory, n: int = 6) -> None:
    client.post("/api/profile", json=PROFILE)
    with db_factory() as db:
        db.add_all(
            [
                Problem(id=i, slug=f"p{i}", title=f"P{i}", difficulty="easy",
                        patterns=["arrays_hashing"], importance=3, lc_id=i)
                for i in range(1, n + 1)
            ]
        )
        db.commit()


def finish(client, problem_id: int) -> None:
    att = client.post("/api/attempts", json={"problem_id": problem_id}).json()
    client.patch(
        f"/api/attempts/{att['id']}",
        json={"outcome": "ac", "duration_sec": 60, "recall_self_report": 5},
    )


def test_snapshot_is_frozen_and_does_not_refill(client, db_factory) -> None:
    seed(client, db_factory)
    first = client.get("/api/plan/today").json()
    ids = [i["problem"]["id"] for i in first["items"]]
    assert len(ids) == 3

    finish(client, ids[0])
    finish(client, ids[1])

    after = client.get("/api/plan/today").json()
    # same three items — no refill — with two checked off
    assert [i["problem"]["id"] for i in after["items"]] == ids
    assert after["done_count"] == 2
    assert after["total_count"] == 3
    dones = {i["problem"]["id"]: i["done"] for i in after["items"]}
    assert dones == {ids[0]: True, ids[1]: True, ids[2]: False}


def test_bonus_appends_without_diluting_progress(client, db_factory) -> None:
    seed(client, db_factory)
    plan = client.get("/api/plan/today").json()
    for item in plan["items"]:
        finish(client, item["problem"]["id"])

    bonus = client.post("/api/plan/bonus").json()
    assert bonus["kind"] == "bonus"
    assert bonus["done"] is False

    after = client.get("/api/plan/today").json()
    assert after["done_count"] == 3 and after["total_count"] == 3  # bonus not in denominator
    assert after["items"][-1]["kind"] == "bonus"

    finish(client, bonus["problem"]["id"])
    assert client.get("/api/plan/today").json()["bonus_done"] == 1


def test_off_plan_problem_shows_as_completed_bonus(client, db_factory) -> None:
    seed(client, db_factory)
    plan = client.get("/api/plan/today").json()
    planned = {i["problem"]["id"] for i in plan["items"]}
    outside = next(pid for pid in range(1, 7) if pid not in planned)

    finish(client, outside)
    after = client.get("/api/plan/today").json()
    extra = next(i for i in after["items"] if i["problem"]["id"] == outside)
    assert extra["kind"] == "bonus" and extra["done"] is True
    assert after["bonus_done"] == 1
    assert after["done_count"] == 0  # plan progress untouched
