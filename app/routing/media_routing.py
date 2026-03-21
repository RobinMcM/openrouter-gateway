"""
Media Routing Configuration for FAL Gateway

Implements:
- Correction #9: Model allowlist to prevent expensive/unsafe model abuse
- Default model selection per media_type
- Configurable sync vs queue mode per model
"""

from typing import Dict, Any, Optional


# Canonical model IDs used for outbound Fal requests.
MODEL_ID_ALIASES: Dict[str, str] = {
    # Legacy ID -> canonical queue endpoint ID.
    "fal-ai/minimax-hailuo-02/image-to-video": "fal-ai/minimax/hailuo-02/standard/image-to-video",
}


def canonicalize_model_id(model: str) -> str:
    candidate = (model or "").strip()
    if not candidate:
        return candidate
    return MODEL_ID_ALIASES.get(candidate, candidate)


# Media routing configuration
# Maps media_type to default model and execution mode
MEDIA_ROUTING_CONFIG: Dict[str, Dict[str, Any]] = {
    "image-generation": {
        "model": "fal-ai/flux/schnell",
        "mode": "queue",  # "sync" or "queue"
        "timeout": 60,
        "description": "Fast image generation with FLUX Schnell"
    },
    "image-generation-hd": {
        "model": "fal-ai/flux-pro",
        "mode": "queue",
        "timeout": 120,
        "description": "High-quality image generation with FLUX Pro"
    },
    "image-to-video": {
        "model": "fal-ai/minimax/hailuo-02/standard/image-to-video",
        "mode": "queue",
        "timeout": 300,
        "description": "Convert image to video with MiniMax Hailuo-02"
    },
    "video-generation": {
        "model": "fal-ai/luma-dream-machine/ray-2-flash",
        "mode": "queue",
        "timeout": 180,
        "description": "Generate video from text with Luma Ray 2 Flash"
    },
    "audio-generation": {
        "model": "fal-ai/stable-audio",
        "mode": "queue",
        "timeout": 120,
        "description": "Generate audio/music with Stable Audio"
    }
}


# Correction #9: Model allowlist
# Only these models can be used (prevents arbitrary expensive model access)
ALLOWED_MODELS = {
    # FLUX image models
    "fal-ai/flux/schnell",
    "fal-ai/flux/dev",
    "fal-ai/flux-pro",
    "fal-ai/flux-pro/v1.1-ultra",
    "fal-ai/flux-2-pro",
    "fal-ai/flux-lora",
    "fal-ai/flux-realism",
    "fal-ai/nano-banana-2",
    "fal-ai/nano-banana-pro",
    "fal-ai/nano-banana",
    "fal-ai/imagen4/preview",
    "fal-ai/gpt-image-1.5",
    "fal-ai/gpt-image-1.5/edit",
    "fal-ai/recraft/v3/text-to-image",
    "fal-ai/ideogram/v3",
    "fal-ai/seedream-v45",
    "fal-ai/stable-diffusion-v35-medium",
    "xai/grok-imagine-image",
    "fal-ai/sana",
    
    # Video models
    "fal-ai/minimax/hailuo-02/standard/image-to-video",
    "fal-ai/kling-video/v1/standard/image-to-video",
    "fal-ai/kling-video/v1/standard/text-to-video",
    "fal-ai/kling-video/v2.5/turbo-pro/image-to-video",
    "fal-ai/kling-video/v3/pro/image-to-video",
    "fal-ai/veo3/image-to-video",
    "fal-ai/veo3.1/image-to-video",
    "wan/v2.6/image-to-video",
    "fal-ai/wan-i2v",
    "xai/grok-imagine-video/image-to-video",
    "fal-ai/runway-gen3/turbo/image-to-video",
    "fal-ai/luma-dream-machine",
    "fal-ai/luma-dream-machine/ray-2",
    "fal-ai/luma-dream-machine/ray-2-flash",
    
    # Audio models
    "fal-ai/stable-audio",
    
    # Add more as needed
}


def get_routing_for_media_type(media_type: str, model_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get routing configuration for a media type.
    
    Args:
        media_type: Type of media to generate
        model_override: Optional model override (must be in ALLOWED_MODELS)
    
    Returns:
        Routing config dict or None if invalid
    """
    # If model override provided, validate it
    if model_override:
        model_override = canonicalize_model_id(model_override)
        if model_override not in ALLOWED_MODELS:
            return None  # Invalid model
        
        # Return routing with override model
        # Use default config for media_type if exists, else create minimal config
        base_config = MEDIA_ROUTING_CONFIG.get(media_type, {
            "mode": "queue",
            "timeout": 180
        })
        
        return {
            "model": model_override,
            "mode": base_config.get("mode", "queue"),
            "timeout": base_config.get("timeout", 180)
        }
    
    # Use default routing for media_type
    if media_type not in MEDIA_ROUTING_CONFIG:
        return None
    
    return MEDIA_ROUTING_CONFIG[media_type].copy()


def is_model_allowed(model: str) -> bool:
    """
    Check if model is in allowlist (Correction #9).
    """
    return canonicalize_model_id(model) in ALLOWED_MODELS


def list_media_types() -> list[str]:
    """List all supported media types"""
    return list(MEDIA_ROUTING_CONFIG.keys())


def _media_type_support_for_model(model: str) -> list[str]:
    key = model.lower()
    if "stable-audio" in key:
        return ["audio-generation"]
    if (
        "image-to-video" in key
        or "text-to-video" in key
        or "kling-video" in key
        or "runway" in key
        or "luma-dream-machine" in key
        or "veo" in key
        or "wan" in key
        or "minimax" in key
        or "grok-imagine-video" in key
    ):
        # Keep both labels for compatibility with clients that use either term.
        return ["image-to-video", "video-generation"]
    return ["image-generation"]


def _display_name_for_model(model: str) -> str:
    tail = model.split("/")[-1]
    return tail.replace("-", " ").replace("_", " ").title()


def list_allowed_models(media_type: Optional[str] = None) -> list[str]:
    """List allowed models, optionally filtered by media type."""
    media = (media_type or "").strip().lower()
    if not media:
        return sorted(ALLOWED_MODELS)
    allowed: list[str] = []
    for model in sorted(ALLOWED_MODELS):
        supports = _media_type_support_for_model(model)
        if media in supports:
            allowed.append(model)
    return allowed


def list_media_models(media_type: Optional[str] = None) -> list[Dict[str, Any]]:
    """Return metadata list used by /api/media/models."""
    selected = list_allowed_models(media_type)
    rows: list[Dict[str, Any]] = []
    for model in selected:
        supports = _media_type_support_for_model(model)
        default_for_media_type = None
        for media_key, cfg in MEDIA_ROUTING_CONFIG.items():
            if cfg.get("model") == model and media_key in supports:
                default_for_media_type = media_key
                break
        rows.append(
            {
                "id": model,
                "name": _display_name_for_model(model),
                "provider": "fal",
                "media_type_support": supports,
                "default_for_media_type": default_for_media_type,
            }
        )
    return rows
