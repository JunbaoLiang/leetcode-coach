"""Today-plan generation (PLAN.md §9.4). Pure functions only — no I/O here."""

from dataclasses import dataclass, field

from app.services.scheduler import review_priority
from app.services.tracks import ml_slots, track_config

NEW_PROBLEM_MINUTES = 40
REVIEW_MINUTES = 20
REVIEW_BUDGET_SHARE = 0.6

# §11.3 default pattern order (primers handled separately, never scheduled as reviews)
PATTERN_ORDER = [
    "arrays_hashing", "two_pointers", "sliding_window", "binary_search", "stack",
    "linked_list", "trees", "bfs", "dfs", "heap", "backtracking", "graphs",
    "dp_1d", "greedy", "intervals",
]

DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}


@dataclass
class DueReview:
    problem_id: int
    importance: int
    overdue_days: int
    ease_factor: float
    review_count: int


@dataclass
class NewCandidate:
    problem_id: int
    patterns: list[str]
    difficulty: str
    importance: int
    is_primer: bool = False
    # mastery == 'learning' and untouched for 3+ days -> beats brand-new problems (§9.4.4)
    is_stale_learning: bool = False


@dataclass
class TodayPlan:
    review_ids: list[int] = field(default_factory=list)
    new_ids: list[int] = field(default_factory=list)
    budget_minutes: int = 0


def _pattern_index(patterns: list[str]) -> int:
    if "primers" in patterns:
        # primers keep their official study-plan order (seed insertion order = problem_id)
        return -1
    for p in patterns:
        if p in PATTERN_ORDER:
            return PATTERN_ORDER.index(p)
    return len(PATTERN_ORDER)


def _pick_new(
    pool: list[NewCandidate],
    new_count: int,
    weak_patterns: list[str],
    weakness_weight: float,
) -> list[NewCandidate]:
    """§9.4.3 — reserve ~weakness_weight of new slots for weak-pattern problems,
    fill the rest in normal curriculum order."""
    ordered = sorted(
        pool,
        key=lambda c: (
            not c.is_stale_learning,
            not c.is_primer,
            _pattern_index(c.patterns),
            DIFFICULTY_RANK.get(c.difficulty, 1),
            -c.importance,
            c.problem_id,
        ),
    )
    if not weak_patterns:
        return ordered[:new_count]

    weak_set = set(weak_patterns)
    weak_slots = round(new_count * weakness_weight)
    # stale-learning and primer picks keep their priority; the bias only steers
    # the truly-new slots
    weak_pool = [
        c for c in ordered
        if set(c.patterns) & weak_set and not c.is_primer and not c.is_stale_learning
    ]
    picked: list[NewCandidate] = weak_pool[:weak_slots]
    picked_ids = {c.problem_id for c in picked}
    for c in ordered:
        if len(picked) >= new_count:
            break
        if c.problem_id not in picked_ids:
            picked.append(c)
            picked_ids.add(c.problem_id)
    # present in curriculum order regardless of how slots were allocated
    return [c for c in ordered if c.problem_id in picked_ids][:new_count]


def build_today_plan(
    weekly_hours: int,
    include_primers: bool,
    due: list[DueReview],
    candidates: list[NewCandidate],
    weak_patterns: list[str] | None = None,
    weakness_weight: float = 0.4,
    track: str = "mle",
    ml_candidates: list[NewCandidate] | None = None,
    ml_unlocked: bool = False,
) -> TodayPlan:
    budget = weekly_hours * 60 / 7

    # 1. due reviews first, by priority, capped at 60% of the daily budget
    max_reviews = int(budget * REVIEW_BUDGET_SHARE // REVIEW_MINUTES)
    ranked = sorted(
        due,
        key=lambda r: review_priority(
            r.importance, r.overdue_days, r.ease_factor, r.review_count
        ),
        reverse=True,
    )
    reviews = ranked[:max_reviews]

    # 2. fill the rest with new problems (stale learning > primers > pattern order)
    remaining = budget - len(reviews) * REVIEW_MINUTES
    new_count = max(0, round(remaining / NEW_PROBLEM_MINUTES))
    if new_count == 0 and not reviews:
        new_count = 1  # a day should never be empty

    # §3.2 — track template: difficulty ceiling for new algo problems + algo:ML mix
    cfg = track_config(track)
    pool = [
        c
        for c in candidates
        if (include_primers or not c.is_primer) and (cfg.allow_hard or c.difficulty != "hard")
    ]
    ml_pool = sorted(ml_candidates or [], key=lambda c: c.problem_id)  # seed order = curriculum
    ml_n = min(ml_slots(track, new_count, ml_unlocked), len(ml_pool))
    news = _pick_new(pool, new_count - ml_n, weak_patterns or [], weakness_weight)
    ml_news = ml_pool[:ml_n]

    return TodayPlan(
        review_ids=[r.problem_id for r in reviews],
        new_ids=[c.problem_id for c in news] + [c.problem_id for c in ml_news],
        budget_minutes=round(budget),
    )
