.PHONY: infra up down api worker migrate seed test test-backend lint build-web build-operator

infra:
	docker compose up -d postgres redis minio minio-init

up:
	docker compose up -d --build

down:
	docker compose down

api:
	cd services/api && uvicorn app.main:app --reload --port 8000

worker:
	cd services && python -m worker.worker

migrate:
	cd services/api && alembic upgrade head

migration:
	cd services/api && alembic revision --autogenerate -m "$(m)"

seed:
	python scripts/seed.py

test-backend:
	cd services/api && python -m pytest -q

lint:
	ruff check services/api services/worker

build-web:
	cd apps/web && npm ci && npm run build

build-operator:
	cd apps/operator && npm ci && npm run build
