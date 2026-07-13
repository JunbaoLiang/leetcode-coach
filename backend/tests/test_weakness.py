from datetime import date, timedelta

from app.services.weakness import (
    AttemptEvidence,
    aggregate_weaknesses,
)

TODAY = date(2026, 7, 13)


def ev(outcome: str, tags: list[str], patterns: list[str], days_ago: int = 0) -> AttemptEvidence:
    return AttemptEvidence(
        outcome=outcome, mistake_tags=tags, patterns=patterns,
        when=TODAY - timedelta(days=days_ago),
    )


def test_empty_history_gives_empty_profile() -> None:
    profile = aggregate_weaknesses([], TODAY)
    assert profile.tags == [] and profile.patterns == [] and profile.weak_patterns == []


def test_tag_counting_and_recency_weighting() -> None:
    profile = aggregate_weaknesses(
        [
            ev("ac", ["off_by_one"], ["arrays_hashing"], days_ago=1),   # weight 1.0
            ev("ac", ["off_by_one"], ["arrays_hashing"], days_ago=90),  # weight 0.5
        ],
        TODAY,
    )
    tag = profile.tags[0]
    assert tag.tag == "off_by_one"
    assert tag.count == 2
    assert tag.weighted == 1.5


def test_recent_errors_dominate_old_ones() -> None:
    # same raw counts: recent edge_case vs old off_by_one -> edge_case ranks first
    profile = aggregate_weaknesses(
        [
            ev("ac", ["edge_case_missed"], ["trees"], days_ago=2),
            ev("ac", ["off_by_one"], ["trees"], days_ago=60),
        ],
        TODAY,
    )
    assert [t.tag for t in profile.tags] == ["edge_case_missed", "off_by_one"]


def test_pattern_error_rate_counts_failures_and_tagged_acs() -> None:
    profile = aggregate_weaknesses(
        [
            ev("failed", [], ["dp_1d"]),                       # error
            ev("ac", ["dp_state_definition"], ["dp_1d"]),      # error (tagged AC)
            ev("ac_first_try", [], ["dp_1d"]),                 # clean
            ev("ac", [], ["dp_1d"]),                           # clean
        ],
        TODAY,
    )
    dp = next(p for p in profile.patterns if p.pattern == "dp_1d")
    assert dp.attempts == 4
    assert dp.error_rate == 0.5


def test_weak_pattern_requires_enough_evidence() -> None:
    # 100% error rate but only 2 weighted attempts -> not enough evidence
    thin = aggregate_weaknesses(
        [ev("failed", [], ["graphs"]), ev("failed", [], ["graphs"])], TODAY
    )
    assert thin.weak_patterns == []
    # 3 weighted attempts at 2/3 error rate -> weak
    solid = aggregate_weaknesses(
        [
            ev("failed", [], ["graphs"]),
            ev("failed", [], ["graphs"]),
            ev("ac_first_try", [], ["graphs"]),
        ],
        TODAY,
    )
    assert solid.weak_patterns == ["graphs"]


def test_primers_excluded_from_pattern_stats() -> None:
    profile = aggregate_weaknesses(
        [ev("failed", [], ["primers", "math"])] * 4, TODAY
    )
    assert all(p.pattern != "primers" for p in profile.patterns)
