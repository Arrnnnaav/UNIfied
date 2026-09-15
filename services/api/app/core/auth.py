from __future__ import annotations
import base64, hashlib, hmac, json, os
from datetime import datetime, timedelta, timezone
from app.core.config import get_settings


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _sign(header: dict, payload: dict, secret: str) -> str:
    encoded = _b64(json.dumps(header, separators=(",", ":")).encode()) + "." + _b64(json.dumps(payload, separators=(",", ":"), default=lambda x: x.isoformat()).encode())
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest()
    return encoded + "." + _b64(signature)


def _decode(token: str, secret: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed token")
    encoded = parts[0] + "." + parts[1]
    expected = _b64(hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, parts[2]):
        raise ValueError("invalid signature")
    padding = "=" * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode((parts[1] + padding).encode()))
    if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
        raise ValueError("expired token")
    return payload

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return base64.urlsafe_b64encode(salt + digest).decode()

def verify_password(password: str, encoded: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(encoded.encode())
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), raw[:16], 180_000)
        return hmac.compare_digest(expected, raw[16:])
    except (ValueError, TypeError):
        return False

def issue_token(user_id: str, role: str) -> str:
    settings = get_settings(); now = datetime.now(timezone.utc)
    return _sign({"alg": "HS256", "typ": "JWT"}, {"sub": user_id, "role": role, "iat": now.timestamp(), "exp": (now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()}, settings.jwt_secret_key)

def decode_token(token: str) -> dict:
    settings = get_settings()
    return _decode(token, settings.jwt_secret_key)
