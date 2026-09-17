.PHONY: infra up down api worker migrate seed test test-backend test-extension test-spatial-core lint build-web test-web build-operator sync-spatial sync-spatial-check package-extension audio

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

test-extension:
	cd apps/extension && node --test tests/geometry.test.mjs

test-spatial-core:
	python -m pytest packages/spatial-core -q

lint:
	ruff check services/api services/worker

build-web:
	cd apps/web && npm ci && npm run build

test-web:
	cd apps/web && npm test

build-operator:
	cd apps/operator && npm ci && npm run build

sync-spatial:
	python scripts/sync_spatial.py

sync-spatial-check:
	python scripts/sync_spatial.py --check

package-extension:
	python scripts/package_extension.py

audio:
	docker compose --profile audio up -d audio-worker
