import hashlib
import json
from typing import Any, Dict, Optional

from app.utils.cache import cache


def _hash_payload(payload: Any) -> str:
    normalized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_cache_key(project_id: str, stage: str, requirements: Any, assets: Any) -> str:
    req_hash = _hash_payload(requirements)
    assets_hash = _hash_payload(assets)
    return f"llm_plan:{project_id}:{stage}:{req_hash}:{assets_hash}"


def get_cached_plan(project_id: str, stage: str, requirements: Any, assets: Any) -> Optional[Dict[str, Any]]:
    key = build_cache_key(project_id, stage, requirements, assets)
    return cache.get(key)


def set_cached_plan(project_id: str, stage: str, requirements: Any, assets: Any, plan: Dict[str, Any], ttl: int = 21600) -> None:
    key = build_cache_key(project_id, stage, requirements, assets)
    cache.set(key, plan, ttl=ttl)
