import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, Optional

from app.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(payload_bytes: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()


def generate_signed_token(payload: Dict[str, Any], ttl_seconds: int) -> str:
    data = dict(payload)
    data["exp"] = int(time.time()) + int(ttl_seconds)
    data["nonce"] = uuid.uuid4().hex
    payload_bytes = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = _sign(payload_bytes, settings.token_signing_keys[0])
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def verify_signed_token(token: str, purpose: str) -> Optional[Dict[str, Any]]:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload_bytes = _b64url_decode(payload_b64)
        signature = _b64url_decode(sig_b64)
        for secret in settings.token_signing_keys:
            expected = _sign(payload_bytes, secret)
            if hmac.compare_digest(signature, expected):
                payload = json.loads(payload_bytes.decode("utf-8"))
                if payload.get("exp", 0) < int(time.time()):
                    return None
                if payload.get("purpose") != purpose:
                    return None
                if not payload.get("project_id"):
                    return None
                return payload
        return None
    except Exception:
        return None
