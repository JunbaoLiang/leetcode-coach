"""Import seed problem metadata into the database (idempotent, upserts by slug).

Usage: .venv/bin/python -m seed.import_seed   (from backend/)
"""

import json
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Problem

SEED_DIR = Path(__file__).resolve().parent
SEED_FILES = ["problems.json", "primers.json", "ml_problems.json"]


def import_file(path: Path) -> tuple[int, int]:
    entries = json.loads(path.read_text())
    created = updated = 0
    with SessionLocal() as db:
        for e in entries:
            existing = db.scalar(select(Problem).where(Problem.slug == e["slug"]))
            if existing is None:
                fields = {k: v for k, v in e.items() if k != "track"}
                db.add(Problem(track=e.get("track", "algo"), **fields))
                created += 1
            else:
                for k, v in e.items():
                    setattr(existing, k, v)
                updated += 1
        db.commit()
    return created, updated


def main() -> None:
    total = 0
    for name in SEED_FILES:
        path = SEED_DIR / name
        if not path.exists():
            continue
        created, updated = import_file(path)
        total += created + updated
        print(f"{name}: {created} created, {updated} updated")
    print(f"total problems in seed: {total}")


if __name__ == "__main__":
    main()
