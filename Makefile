PY := backend/.venv/bin/python

.PHONY: backup restore seed dev-backend dev-frontend test lint

backup:
	cd backend && .venv/bin/python -m scripts.backup

# usage: make restore FILE=backups/snapshot_20260713_1200.json
restore:
ifndef FILE
	$(error usage: make restore FILE=backups/snapshot_YYYYMMDD_HHMM.json)
endif
	cd backend && .venv/bin/python -m scripts.restore ../$(FILE)

seed:
	cd backend && .venv/bin/python -m seed.import_seed

dev-backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest -q

lint:
	cd backend && .venv/bin/ruff check app tests alembic scripts seed
