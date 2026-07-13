"""Track templates (PLAN.md §3.2). Pure config + functions — no I/O here.

Each track decides the algo:ML mix of new problems, the difficulty ceiling,
and when ML coding unlocks (as a fraction of algo-curriculum progress).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackConfig:
    ml_share: float  # share of new-problem slots that go to ML coding
    allow_hard: bool  # difficulty ceiling for NEW algo problems
    # ML problems unlock once solved_algo/total_algo reaches this fraction
    ml_unlock_progress: float


TRACKS: dict[str, TrackConfig] = {
    # 算法 70 : ML 30,medium 为主少量 hard,ML 从课程 1/3 处引入
    "mle": TrackConfig(ml_share=0.3, allow_hard=True, ml_unlock_progress=1 / 3),
    # 算法 60 : ML 40,medium 上限,强化数值题(ML 题本身偏数值)
    "ai4s": TrackConfig(ml_share=0.4, allow_hard=False, ml_unlock_progress=1 / 3),
    # 纯算法,完整覆盖含 hard
    "swe_newgrad": TrackConfig(ml_share=0.0, allow_hard=True, ml_unlock_progress=1.0),
    # 算法 80 : ML 20,easy→medium 缓坡,primers 热身在 planner 中单独处理
    "career_switch": TrackConfig(ml_share=0.2, allow_hard=False, ml_unlock_progress=1 / 3),
}


def track_config(track: str) -> TrackConfig:
    return TRACKS.get(track, TRACKS["mle"])


def ml_unlocked(track: str, solved_algo: int, total_algo: int) -> bool:
    cfg = track_config(track)
    if cfg.ml_share == 0 or total_algo == 0:
        return False
    return solved_algo / total_algo >= cfg.ml_unlock_progress


def ml_slots(track: str, new_count: int, unlocked: bool) -> int:
    """How many of today's new-problem slots go to ML coding."""
    if not unlocked:
        return 0
    return round(new_count * track_config(track).ml_share)
