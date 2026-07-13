from app.services.planner import DueReview, NewCandidate, build_today_plan


def dr(
    pid: int, importance: int = 3, overdue: int = 0, ef: float = 2.5, count: int = 1
) -> DueReview:
    return DueReview(pid, importance, overdue, ef, count)


def nc(pid: int, patterns: list[str], diff: str = "easy", imp: int = 3, **kw) -> NewCandidate:
    return NewCandidate(pid, patterns, diff, imp, **kw)


def test_reviews_capped_at_60_percent_of_budget() -> None:
    # 14h/week -> 120 min/day -> at most 72 min of reviews -> 3 reviews
    plan = build_today_plan(14, False, [dr(i) for i in range(10)], [])
    assert len(plan.review_ids) == 3
    assert plan.budget_minutes == 120


def test_high_priority_review_goes_first() -> None:
    plan = build_today_plan(
        14, False,
        [dr(1, importance=2, overdue=0), dr(2, importance=4, overdue=5)],
        [],
    )
    assert plan.review_ids[0] == 2


def test_new_problems_follow_pattern_order() -> None:
    plan = build_today_plan(
        14, False, [],
        [nc(1, ["two_pointers"]), nc(2, ["arrays_hashing"]), nc(3, ["dp_1d"])],
    )
    assert plan.new_ids[:2] == [2, 1]


def test_stale_learning_beats_brand_new() -> None:
    plan = build_today_plan(
        14, False, [],
        [nc(1, ["arrays_hashing"], imp=4), nc(2, ["dp_1d"], is_stale_learning=True)],
    )
    assert plan.new_ids[0] == 2


def test_primers_first_when_enabled_and_excluded_when_disabled() -> None:
    cands = [nc(1, ["arrays_hashing"], imp=4), nc(2, ["primers", "math"], imp=1, is_primer=True)]
    with_primers = build_today_plan(14, True, [], cands)
    without = build_today_plan(14, False, [], cands)
    assert with_primers.new_ids[0] == 2
    assert 2 not in without.new_ids


def test_day_never_empty_even_on_tiny_budget() -> None:
    plan = build_today_plan(1, False, [], [nc(1, ["arrays_hashing"])])
    assert plan.new_ids == [1]


def test_weakness_bias_reserves_slots_for_weak_patterns() -> None:
    # 120-min budget -> 3 new slots; dp_1d is weak -> round(3*0.4)=1 slot reserved
    cands = [
        nc(1, ["arrays_hashing"], imp=4),
        nc(2, ["two_pointers"], imp=4),
        nc(3, ["sliding_window"], imp=4),
        nc(4, ["dp_1d"], imp=3),  # far down the curriculum, pulled in by the bias
    ]
    plan = build_today_plan(14, False, [], cands, weak_patterns=["dp_1d"], weakness_weight=0.4)
    assert 4 in plan.new_ids
    assert len(plan.new_ids) == 3


def test_no_weakness_bias_without_weak_patterns() -> None:
    cands = [
        nc(1, ["arrays_hashing"], imp=4),
        nc(2, ["two_pointers"], imp=4),
        nc(3, ["sliding_window"], imp=4),
        nc(4, ["dp_1d"], imp=3),
    ]
    plan = build_today_plan(14, False, [], cands)
    assert plan.new_ids == [1, 2, 3]


def test_weakness_weight_configurable() -> None:
    # weight 1.0 -> all 3 slots go to the weak pattern
    cands = [
        nc(1, ["arrays_hashing"], imp=4),
        nc(2, ["dp_1d"], imp=3),
        nc(3, ["dp_1d"], imp=3),
        nc(4, ["dp_1d"], imp=2),
    ]
    plan = build_today_plan(14, False, [], cands, weak_patterns=["dp_1d"], weakness_weight=1.0)
    assert plan.new_ids == [2, 3, 4]
