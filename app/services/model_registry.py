import time
from typing import Any, Dict, List, Optional

from app.routing.media_routing import list_media_models

_CACHE_TTL_SECONDS = 300
_CACHE: Dict[str, Any] = {
    "expires_at": 0.0,
    "models": [],
    "fetched_at": None,
}


def _query_type_to_media_types(query_type: Optional[str]) -> Optional[set[str]]:
    qt = (query_type or "").strip().lower()
    if not qt:
        return None
    mapping = {
        "text-image": {"image-generation"},
        "image-video": {"image-to-video", "video-generation"},
        "text-music": {"audio-generation"},
    }
    return mapping.get(qt)


def get_dynamic_media_models(*, query_type: Optional[str] = None, media_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Return media models with short-lived cache and optional filtering.
    This is the gateway source-of-truth for model discovery endpoints.
    """
    now = time.time()
    if now >= float(_CACHE.get("expires_at") or 0):
        rows = list_media_models(media_type=None)
        _CACHE["models"] = rows
        _CACHE["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _CACHE["expires_at"] = now + _CACHE_TTL_SECONDS

    models: List[Dict[str, Any]] = list(_CACHE.get("models") or [])
    if media_type:
        target = media_type.strip().lower()
        models = [m for m in models if target in [str(x).strip().lower() for x in (m.get("media_type_support") or [])]]

    supported = _query_type_to_media_types(query_type)
    if supported:
        models = [
            m
            for m in models
            if any(str(x).strip().lower() in supported for x in (m.get("media_type_support") or []))
        ]

    return {
        "models": models,
        "fetched_at": _CACHE.get("fetched_at"),
        "cache_ttl_seconds": _CACHE_TTL_SECONDS,
    }
