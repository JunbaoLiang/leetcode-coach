from app.services.planner import NewCandidate, build_today_plan
from app.services.tracks import ml_slots, ml_unlocked


def algo(pid: int, diff: str = "medium", imp: int = 3) -> NewCandidate:
    return NewCandidate(pid, ["arrays_hashing"], diff, imp)


def ml(pid: int) -> NewCandidate:
    return NewCandidate(pid, ["ml_coding"], "medium", 4)


def test_ml_unlocks_at_one_third_progress() -> None:
    assert not ml_unlocked("mle", solved_algo=10, total_algo=150)
    assert ml_unlocked("mle", solved_algo=50, total_algo=150)
    # swe track never unlocks ML
    assert not ml_unlocked("swe_newgrad", solved_algo=150, total_algo=150)


def test_ml_share_per_track() -> None:
    assert ml_slots("mle", 10, unlocked=True) == 3       # 70:30
    assert ml_slots("ai4s", 10, unlocked=True) == 4      # 60:40
    assert ml_slots("career_switch", 10, unlocked=True) == 2  # 80:20
    assert ml_slots("swe_newgrad", 10, unlocked=True) == 0
    assert ml_slots("mle", 10, unlocked=False) == 0


def test_plan_mixes_ml_when_unlocked() -> None:
    # 14h/week -> 3 new slots; mle 30% -> 1 ML slot
    plan = build_today_plan(
        14, False, [], [algo(1), algo(2), algo(3)],
        track="mle", ml_candidates=[ml(101), ml(102)], ml_unlocked=True,
    )
    assert len(plan.new_ids) == 3
    assert 101 in plan.new_ids  # first ML problem in seed order
    assert 102 not in plan.new_ids


def test_plan_all_algo_before_unlock() -> None:
    plan = build_today_plan(
        14, False, [], [algo(1), algo(2), algo(3)],
        track="mle", ml_candidates=[ml(101)], ml_unlocked=False,
    )
    assert plan.new_ids == [1, 2, 3]


def test_difficulty_cap_for_gentler_tracks() -> None:
    cands = [algo(1, "hard", 4), algo(2, "medium"), algo(3, "easy")]
    capped = build_today_plan(14, False, [], cands, track="career_switch")
    assert 1 not in capped.new_ids
    uncapped = build_today_plan(14, False, [], cands, track="swe_newgrad")
    assert 1 in uncapped.new_ids
