.PHONY: dev db-up db-down backend-install backend-dev backend-test backend-lint backend-typecheck frontend-install frontend-dev frontend-test frontend-typecheck frontend-build check

# --- Dev environment ---
# Only PostgreSQL runs in Docker; backend and frontend run locally (venv/npm)
# for fast iteration. See docker-compose.yml (single `db` service).
dev: db-up
	@echo "DB up. Start backend (uvicorn) + frontend (vite) separately:"
	@echo "  make backend-dev"
	@echo "  make frontend-dev"

db-up:
	docker compose up -d db

db-down:
	docker compose down

# --- Backend ---
backend-install:
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install -e "backend[dev]"

backend-dev:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && .venv/bin/pytest

backend-lint:
	cd backend && .venv/bin/ruff check .

backend-typecheck:
	cd backend && .venv/bin/mypy app

# --- Frontend ---
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm run test

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-build:
	cd frontend && npm run build

# --- Combined checks (CI) ---
check: backend-lint backend-typecheck backend-test frontend-typecheck frontend-test
	@echo "All checks passed."
