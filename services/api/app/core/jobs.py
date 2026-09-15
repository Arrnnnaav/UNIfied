from __future__ import annotations

import json
import os
import time
from typing import Any


def enqueue_optional(job_id: str, kind: str, payload: dict[str, Any]) -> bool:
    """Return False when Redis is not configured/reachable; the API can use its local fallback."""
    if os.getenv("ASYNC_INGESTION", "false").lower() != "true":
        return False
    try:
        import redis
        client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=0.25)
        client.rpush(os.getenv("REDIS_QUEUE", "learning-platform:jobs"), json.dumps({"id": job_id, "kind": kind, "payload": payload, "queued_at": time.time()}))
        return True
    except Exception:
        return False
