import random
from datetime import date, timedelta

import pytest

from app.services.scheduler import (
    IMPORTANCE_MULTIPLIER,
    JITTER_RANGE,
    MIN_EASE_FACTOR,
    compute_quality,
    review_priority,
    update_review,
)

TODAY = date(2026, 7, 13)


def fixed_rng(value: float) -> random.Random:
    """An rng whose uniform() always returns ``value`` (must lie inside JITTER_RANGE)."""
    assert JITTER_RANGE[0] <= value <= JITTER_RANGE[1]

    class _Fixed(random.Random):
        def uniform(self, a: float, b: float) -> float:
            return value

    return _Fixed()


NO_JITTER = fixed_rng(1.0)


# --- §9.1 quality synthesis -------------------------------------------------


def test_quality_perfect_first_try_caps_at_5() -> None:
    assert compute_quality(5, hint_level_max=0, judge_failures=0, outcome="ac_first_try") == 5.0


def test_quality_hint_levels_subtract_half_each() -> None:
    assert compute_quality(4, hint_level_max=3, judge_failures=0, outcome="ac") == 2.5


def test_quality_judge_failures_capped_at_penalty_1_5() -> None:
    # 10 failures penalize the same as 3
    assert compute_quality(5, 0, judge_failures=10, outcome="ac") == compute_quality(
        5, 0, judge_failures=3, outcome="ac"
    )
    assert compute_quality(5, 0, judge_failures=10, outcome="ac") == 3.5


def test_quality_clamped_to_zero() -> None:
    assert compute_quality(0, hint_level_max=4, judge_failures=3, outcome="failed") == 0.0


def test_quality_first_try_bonus() -> None:
    base = compute_quality(3, 0, 0, outcome="ac")
    bonus = compute_quality(3, 0, 0, outcome="ac_first_try")
    assert bonus - base == 0.5


# --- §9.2 interval update ---------------------------------------------------


def test_lapse_resets_interval_and_count_keeps_ef() -> None:
    st = update_review(
        ease_factor=2.5, interval_days=20, review_count=5, q=2.0, importance=2, today=TODAY,
        rng=NO_JITTER,
    )
    assert st.interval_days == 1
    assert st.review_count == 0
    assert st.ease_factor == 2.5
    assert st.due_date == TODAY + timedelta(days=1)


def test_first_review_interval_is_1() -> None:
    st = update_review(2.5, 0, 0, q=4.0, importance=2, today=TODAY, rng=NO_JITTER)
    assert st.interval_days == 1
    assert st.review_count == 1


def test_second_review_interval_is_3() -> None:
    st = update_review(2.5, 1, 1, q=4.0, importance=2, today=TODAY, rng=NO_JITTER)
    assert st.interval_days == 3
    assert st.review_count == 2


def test_third_review_multiplies_by_ef() -> None:
    st = update_review(2.5, 6, 2, q=5.0, importance=2, today=TODAY, rng=NO_JITTER)
    # EF grows to 2.6 on q=5, then 6 * 2.6 = 15.6 -> round 16
    assert st.ease_factor == pytest.approx(2.6)
    assert st.interval_days == 16


def test_ef_floor_1_3() -> None:
    st = update_review(1.3, 3, 2, q=3.0, importance=2, today=TODAY, rng=NO_JITTER)
    assert st.ease_factor == MIN_EASE_FACTOR


def test_importance_4_shortens_interval() -> None:
    base = update_review(2.5, 10, 3, q=4.0, importance=2, today=TODAY, rng=NO_JITTER)
    hot = update_review(2.5, 10, 3, q=4.0, importance=4, today=TODAY, rng=NO_JITTER)
    assert hot.interval_days == round(base.interval_days * IMPORTANCE_MULTIPLIER[4])
    assert hot.interval_days < base.interval_days


def test_importance_1_stretches_interval() -> None:
    base = update_review(2.5, 10, 3, q=4.0, importance=2, today=TODAY, rng=NO_JITTER)
    cold = update_review(2.5, 10, 3, q=4.0, importance=1, today=TODAY, rng=NO_JITTER)
    assert cold.interval_days > base.interval_days


def test_jitter_bounds_respected() -> None:
    lo = update_review(2.5, 10, 3, q=4.0, importance=2, today=TODAY, rng=fixed_rng(0.9))
    hi = update_review(2.5, 10, 3, q=4.0, importance=2, today=TODAY, rng=fixed_rng(1.1))
    assert lo.interval_days < hi.interval_days
    # real rng always lands inside the two fixed extremes
    for seed in range(20):
        st = update_review(2.5, 10, 3, q=4.0, importance=2, today=TODAY, rng=random.Random(seed))
        assert lo.interval_days <= st.interval_days <= hi.interval_days


def test_interval_never_below_1_day() -> None:
    st = update_review(2.5, 0, 0, q=3.0, importance=4, today=TODAY, rng=fixed_rng(0.9))
    assert st.interval_days >= 1


def test_q_boundary_3_is_not_a_lapse() -> None:
    st = update_review(2.5, 6, 2, q=3.0, importance=2, today=TODAY, rng=NO_JITTER)
    assert st.review_count == 3  # progressed, not reset


# --- §9.3 priority ----------------------------------------------------------


def test_priority_favors_importance_and_overdue() -> None:
    urgent = review_priority(importance=4, overdue_days=4, ease_factor=2.5, review_count=1)
    fresh = review_priority(importance=2, overdue_days=0, ease_factor=2.5, review_count=1)
    assert urgent > fresh


def test_priority_penalizes_easy_well_reviewed_items() -> None:
    hard_item = review_priority(3, 0, ease_factor=1.3, review_count=0)
    easy_item = review_priority(3, 0, ease_factor=2.8, review_count=6)
    assert hard_item > easy_item
