"""Restore user data from a JSON snapshot produced by scripts.backup.

Usage: .venv/bin/python -m scripts.restore <snapshot.json>   (from backend/)

Replaces ALL user data (users/attempts/hint_events/reviews/mock_sessions/reports)
with the snapshot contents. Problems (seed-managed) are untouched.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete, inspect

from app.db import SessionLocal
from app.models import Attempt, HintEvent, MockSession, Report, Review, User

MODELS = {m.__tablename__: m for m in [User, Attempt, HintEvent, Review, MockSession, Report]}


def coerce(model, row: dict) -> dict:
    """ISO strings back to date/datetime according to column types."""
    out = dict(row)
    for col in inspect(model).columns:
        val = out.get(col.key)
        if val is None or not isinstance(val, str):
            continue
        py = col.type.python_type
        if py is datetime:
            out[col.key] = datetime.fromisoformat(val)
        elif py is date:
            out[col.key] = date.fromisoformat(val)
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.restore <snapshot.json>")
    path = Path(sys.argv[1])
    snapshot = json.loads(path.read_text())
    unknown = set(snapshot) - set(MODELS)
    if unknown:
        sys.exit(f"snapshot contains unknown tables: {sorted(unknown)}")

    with SessionLocal() as db:
        # children first on delete, parents first on insert
        for name in ["hint_events", "mock_sessions", "reports", "reviews", "attempts", "users"]:
            db.execute(delete(MODELS[name]))
        for name in ["users", "attempts", "hint_events", "reviews", "mock_sessions", "reports"]:
            model = MODELS[name]
            for row in snapshot.get(name, []):
                db.add(model(**coerce(model, row)))
        db.commit()
    counts = ", ".join(f"{k}={len(v)}" for k, v in snapshot.items())
    print(f"restored from {path}: {counts}")


if __name__ == "__main__":
    main()
