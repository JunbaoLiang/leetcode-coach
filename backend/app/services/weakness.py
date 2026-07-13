"""Weakness-profile aggregation (PLAN §10 / M2). Pure functions only — no I/O here.

Error evidence = attempts that failed/were abandoned, or that AC'd but carry
mistake tags. Recent attempts (≤30 days) weigh double vs older ones.
"""

from dataclasses import dataclass, field
from datetime import date

RECENT_DAYS = 30
RECENT_WEIGHT = 1.0
OLD_WEIGHT = 0.5

# a pattern only counts as weak with enough evidence and a high error rate
MIN_PATTERN_EVIDENCE = 3.0  # weighted attempts
WEAK_RATE_THRESHOLD = 0.4


@dataclass
class AttemptEvidence:
    outcome: str  # ac_first_try|ac|failed|abandoned
    mistake_tags: list[str]
    patterns: list[str]
    when: date


@dataclass
class TagStat:
    tag: str
    count: int = 0  # raw occurrences
    weighted: float = 0.0  # recency-weighted occurrences
    rate: float = 0.0  # weighted share of attempts carrying this tag


@dataclass
class PatternStat:
    pattern: str
    attempts: int = 0
    weighted_attempts: float = 0.0
    weighted_errors: float = 0.0
    error_rate: float = 0.0


@dataclass
class WeaknessProfile:
    tags: list[TagStat] = field(default_factory=list)
    patterns: list[PatternStat] = field(default_factory=list)
    weak_patterns: list[str] = field(default_factory=list)


def _weight(when: date, today: date) -> float:
    return RECENT_WEIGHT if (today - when).days <= RECENT_DAYS else OLD_WEIGHT


def _is_error(a: AttemptEvidence) -> bool:
    return a.outcome in ("failed", "abandoned") or bool(a.mistake_tags)


def aggregate_weaknesses(attempts: list[AttemptEvidence], today: date) -> WeaknessProfile:
    if not attempts:
        return WeaknessProfile()

    total_weight = sum(_weight(a.when, today) for a in attempts)

    tag_stats: dict[str, TagStat] = {}
    for a in attempts:
        w = _weight(a.when, today)
        for tag in a.mistake_tags:
            st = tag_stats.setdefault(tag, TagStat(tag=tag))
            st.count += 1
            st.weighted += w
    for st in tag_stats.values():
        st.rate = round(st.weighted / total_weight, 3)

    pattern_stats: dict[str, PatternStat] = {}
    for a in attempts:
        w = _weight(a.when, today)
        err = _is_error(a)
        for pattern in a.patterns:
            if pattern == "primers":
                continue
            ps = pattern_stats.setdefault(pattern, PatternStat(pattern=pattern))
            ps.attempts += 1
            ps.weighted_attempts += w
            if err:
                ps.weighted_errors += w
    for ps in pattern_stats.values():
        ps.error_rate = round(ps.weighted_errors / ps.weighted_attempts, 3)

    weak = [
        ps.pattern
        for ps in pattern_stats.values()
        if ps.weighted_attempts >= MIN_PATTERN_EVIDENCE and ps.error_rate >= WEAK_RATE_THRESHOLD
    ]
    return WeaknessProfile(
        tags=sorted(tag_stats.values(), key=lambda s: -s.weighted),
        patterns=sorted(pattern_stats.values(), key=lambda s: -s.error_rate),
        weak_patterns=sorted(weak, key=lambda p: -pattern_stats[p].error_rate),
    )
