"""Evidence-driven SM-2 scheduler (PLAN.md §9). Pure functions only — no I/O here."""

import random
from dataclasses import dataclass
from datetime import date, timedelta

# §9.2 — importance 4 (must-know) reviews 25% more often; importance 1 20% less often
IMPORTANCE_MULTIPLIER = {4: 0.75, 3: 0.9, 2: 1.0, 1: 1.2}

MIN_EASE_FACTOR = 1.3
JITTER_RANGE = (0.9, 1.1)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_quality(
    recall_self_report: float,
    hint_level_max: int,
    judge_failures: int,
    outcome: str,
) -> float:
    """§9.1 — synthesize quality q ∈ [0, 5] from self-report plus objective evidence."""
    q = (
        recall_self_report
        - 0.5 * hint_level_max
        - 0.5 * min(judge_failures, 3)
        + (0.5 if outcome == "ac_first_try" else 0.0)
    )
    return clamp(q, 0.0, 5.0)


@dataclass
class ReviewState:
    ease_factor: float
    interval_days: int
    review_count: int
    due_date: date


def update_review(
    ease_factor: float,
    interval_days: int,
    review_count: int,
    q: float,
    importance: int,
    today: date,
    rng: random.Random | None = None,
) -> ReviewState:
    """§9.2 — SM-2 interval update. Pass a seeded ``rng`` for deterministic tests."""
    if q < 3:
        interval = 1.0
        review_count = 0
        # PLAN §9.2: on a lapse the item restarts its interval ladder, EF is left unchanged
        ef = ease_factor
    else:
        ef = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        ef = max(ef, MIN_EASE_FACTOR)
        if review_count == 0:
            interval = 1.0
        elif review_count == 1:
            interval = 3.0
        else:
            interval = float(round(interval_days * ef))
        review_count += 1

    interval *= IMPORTANCE_MULTIPLIER[importance]
    jitter = (rng or random).uniform(*JITTER_RANGE)
    interval *= jitter
    interval_out = max(1, round(interval))
    return ReviewState(
        ease_factor=ef,
        interval_days=interval_out,
        review_count=review_count,
        due_date=today + timedelta(days=interval_out),
    )


def review_priority(
    importance: int,
    overdue_days: int,
    ease_factor: float,
    review_count: int,
) -> float:
    """§9.3 — which due review goes first when there is a backlog."""
    return 1.5 * importance + 0.5 * overdue_days - 1.0 * ease_factor - 0.5 * review_count
