from typing import Any, Dict, Optional, Tuple

from app.routing.media_routing import canonicalize_model_id


def _to_media_type(query_type: str) -> str:
    qt = (query_type or "").strip().lower()
    mapping = {
        "text-image": "image-generation",
        "image-video": "image-to-video",
        "text-music": "audio-generation",
        "text": "text-generation",
    }
    return mapping.get(qt, "")


def _family(model_id: str) -> str:
    key = (model_id or "").strip().lower()
    if "minimax" in key or "hailuo" in key:
        return "minimax_hailuo"
    if "kling-video" in key:
        return "kling"
    if "veo3" in key:
        return "veo"
    if "wan/" in key or "wan-i2v" in key:
        return "wan"
    if "stable-audio" in key:
        return "stable_audio"
    if "flux" in key or "imagen" in key or "recraft" in key or "ideogram" in key:
        return "text_image"
    return "generic"


def transform_generic_request(
    *,
    query_type: str,
    model: str,
    source_image: Optional[str],
    options: Optional[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Transform generic request into provider payload.
    Returns (media_type, payload, transform_trace).
    """
    media_type = _to_media_type(query_type)
    if not media_type:
        raise ValueError(f"Unsupported query_type: {query_type}")

    canonical_model = canonicalize_model_id(model)
    family = _family(canonical_model)
    opts = dict(options or {})
    accepted_fields: list[str] = []
    dropped_fields: list[str] = []
    defaulted_fields: Dict[str, Any] = {}

    # Base prompt normalization
    prompt = str(opts.get("prompt") or "").strip()
    if not prompt:
        prompt = "Cinematic shot"
        defaulted_fields["prompt"] = prompt
    payload: Dict[str, Any] = {"prompt": prompt}
    accepted_fields.append("prompt")

    if media_type == "image-to-video":
        image_url = str(source_image or opts.get("source_image") or opts.get("image_url") or "").strip()
        if not image_url:
            raise ValueError("source_image (or options.image_url) is required for image-video.")
        payload["image_url"] = image_url
        accepted_fields.append("image_url")

    # Family-based option allowlists/defaults
    allowed: Dict[str, Any] = {}
    if family == "minimax_hailuo":
        allowed = {
            "duration": "6",
            "resolution": "768P",
            "prompt_optimizer": True,
            "seed": None,
            "end_image_url": None,
        }
    elif family == "kling":
        allowed = {"duration": "5", "aspect_ratio": "16:9", "negative_prompt": "", "cfg_scale": 0.5, "seed": None}
    elif family == "veo":
        allowed = {"duration": "6s", "aspect_ratio": "16:9", "resolution": "720p", "generate_audio": True, "seed": None}
    elif family == "wan":
        allowed = {"duration": "5", "resolution": "720p", "enable_prompt_rewriting": True, "negative_prompt": "", "seed": None}
    elif family == "stable_audio":
        allowed = {"duration": 30, "seed": None}
    elif family == "text_image":
        allowed = {"aspect_ratio": "1:1", "image_size": "square_hd", "seed": None}
    else:
        allowed = {"duration": "5", "aspect_ratio": "16:9", "seed": None}

    for key, default_value in allowed.items():
        if key in opts and opts[key] is not None and str(opts[key]).strip() != "":
            payload[key] = opts[key]
            accepted_fields.append(key)
        elif default_value is not None:
            payload[key] = default_value
            defaulted_fields[key] = default_value

    # Track dropped unknown option keys
    for key in opts.keys():
        if key == "prompt":
            continue
        if key not in allowed and key not in {"source_image", "image_url"}:
            dropped_fields.append(key)

    trace = {
        "query_type": query_type,
        "media_type": media_type,
        "requested_model": model,
        "canonical_model": canonical_model,
        "model_family": family,
        "accepted_fields": accepted_fields,
        "defaulted_fields": defaulted_fields,
        "dropped_fields": dropped_fields,
    }
    return media_type, payload, trace
