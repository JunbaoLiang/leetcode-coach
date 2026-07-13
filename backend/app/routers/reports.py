import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Attempt, Report
from app.routers.plan import compute_streak
from app.routers.profile import get_current_user
from app.schemas import ReportOut, ReportSummary
from app.services import llm
from app.services.weakness import AttemptEvidence, aggregate_weaknesses

router = APIRouter(prefix="/api")


def _slice_metrics(attempts: list[Attempt]) -> dict:
    """Aggregate one week's finished attempts into plain numbers (backend-computed;
    the LLM only narrates, per §8.5)."""
    n = len(attempts)
    if n == 0:
        return {"attempts": 0}
    ac = [a for a in attempts if a.outcome in ("ac", "ac_first_try")]
    first = [a for a in attempts if a.outcome == "ac_first_try"]
    tags: dict[str, int] = {}
    for a in attempts:
        for t in a.mistake_tags or []:
            tags[t] = tags.get(t, 0) + 1
    return {
        "attempts": n,
        "distinct_problems": len({a.problem_id for a in attempts}),
        "ac_rate": round(len(ac) / n, 3),
        "ac_first_try_rate": round(len(first) / n, 3),
        "avg_hint_level": round(sum(a.hint_level_max for a in attempts) / n, 2),
        "mistake_tag_counts": dict(sorted(tags.items(), key=lambda kv: -kv[1])),
    }


def build_week_metrics(db: Session, user_id: int, today: date) -> dict:
    period_start = today - timedelta(days=6)
    prev_start = today - timedelta(days=13)
    finished = list(
        db.scalars(
            select(Attempt).where(Attempt.user_id == user_id, Attempt.outcome.is_not(None))
        )
    )
    this_week = [a for a in finished if a.created_at.date() >= period_start]
    prev_week = [
        a for a in finished if prev_start <= a.created_at.date() < period_start
    ]
    cur, prev = _slice_metrics(this_week), _slice_metrics(prev_week)

    cur_tags = set(cur.get("mistake_tag_counts", {}))
    prev_tags = set(prev.get("mistake_tag_counts", {}))
    profile = aggregate_weaknesses(
        [
            AttemptEvidence(
                outcome=a.outcome,
                mistake_tags=a.mistake_tags or [],
                patterns=a.problem.patterns,
                when=a.created_at.date(),
            )
            for a in finished
        ],
        today,
    )
    return {
        "period_start": period_start.isoformat(),
        "period_end": today.isoformat(),
        "this_week": cur,
        "previous_week": prev,
        "new_mistake_tags": sorted(cur_tags - prev_tags),
        "receded_mistake_tags": sorted(prev_tags - cur_tags),
        "weak_patterns": profile.weak_patterns,
        "streak_days": compute_streak(db, user_id, today),
    }


@router.post("/reports/weekly", response_model=ReportOut)
async def generate_weekly_report(db: Session = Depends(get_db)) -> Report:
    user = get_current_user(db)
    if user is None:
        raise HTTPException(404, "no profile yet")
    today = date.today()
    metrics = build_week_metrics(db, user.id, today)
    if metrics["this_week"]["attempts"] == 0:
        raise HTTPException(422, "本周没有任何做题记录,先刷题再来生成周报")

    system = llm.load_prompt(
        "reporter",
        metrics_json=json.dumps(metrics, ensure_ascii=False, indent=1),
        background=user.background or "(未填写)",
        target_track=user.target_track,
        period_start=metrics["period_start"],
        period_end=metrics["period_end"],
    )
    try:
        content_md = await llm.completion(
            system, [{"role": "user", "content": "请生成本周周报。"}]
        )
    except llm.LLMNotConfiguredError as e:
        raise HTTPException(503, str(e)) from e

    report = Report(
        user_id=user.id,
        period_start=date.fromisoformat(metrics["period_start"]),
        period_end=today,
        content_md=content_md,
        metrics=metrics,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/reports", response_model=list[ReportSummary])
def list_reports(db: Session = Depends(get_db)) -> list[Report]:
    user = get_current_user(db)
    if user is None:
        raise HTTPException(404, "no profile yet")
    return list(
        db.scalars(
            select(Report).where(Report.user_id == user.id).order_by(Report.id.desc())
        )
    )


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "report not found")
    return report
