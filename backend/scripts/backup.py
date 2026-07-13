"""Export all user data to a timestamped JSON snapshot (data-level rollback, PLAN §4.1).

Usage: .venv/bin/python -m scripts.backup   (from backend/)
"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, select

from app.db import SessionLocal
from app.models import Attempt, HintEvent, MockSession, Report, Review, User

BACKUPS_DIR = Path(__file__).resolve().parent.parent.parent / "backups"

# problems are seed-managed, everything else is user data
TABLES = [User, Attempt, HintEvent, Review, MockSession, Report]


def row_to_dict(obj) -> dict:
    out = {}
    for col in inspect(obj.__class__).columns:
        val = getattr(obj, col.key)
        out[col.key] = val.isoformat() if hasattr(val, "isoformat") else val
    return out


def main() -> None:
    BACKUPS_DIR.mkdir(exist_ok=True)
    snapshot: dict[str, list[dict]] = {}
    with SessionLocal() as db:
        for model in TABLES:
            snapshot[model.__tablename__] = [
                row_to_dict(o) for o in db.scalars(select(model))
            ]
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    path = BACKUPS_DIR / f"snapshot_{stamp}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1))
    counts = ", ".join(f"{k}={len(v)}" for k, v in snapshot.items())
    print(f"wrote {path}")
    print(f"rows: {counts}")


if __name__ == "__main__":
    main()
