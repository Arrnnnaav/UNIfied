#!/bin/sh
# Container start for App Runner / any single-container host: migrate, then serve.
set -e
cd /workspace/services/api
if [ -n "$DATABASE_URL" ]; then
  echo "[entrypoint] alembic upgrade head"
  (cd /workspace && alembic upgrade head) || echo "[entrypoint] migration failed; continuing (dev schema bridge will cover sqlite)"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
