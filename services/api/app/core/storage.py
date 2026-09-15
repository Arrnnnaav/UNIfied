from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.getenv("LP_STORAGE_DIR", ".data/uploads"))


def _s3_client():
    if os.getenv("STORAGE_BACKEND", "local").lower() != "s3":
        return None
    import boto3
    from app.core.config import get_settings
    settings = get_settings()
    return boto3.client("s3", endpoint_url=settings.s3_endpoint_url,
                        aws_access_key_id=settings.s3_access_key,
                        aws_secret_access_key=settings.s3_secret_key,
                        region_name="us-east-1")


def put_bytes(key: str, payload: bytes) -> str:
    client = _s3_client()
    if client:
        from app.core.config import get_settings
        client.put_object(Bucket=get_settings().s3_bucket, Key=key, Body=payload)
        return key
    path = ROOT / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return str(path)


def get_bytes(key: str) -> bytes:
    client = _s3_client()
    if client:
        from app.core.config import get_settings
        return client.get_object(Bucket=get_settings().s3_bucket, Key=key)["Body"].read()
    return (ROOT / key).read_bytes()
