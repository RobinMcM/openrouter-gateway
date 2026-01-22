"""
Media Routing Configuration for FAL Gateway

Implements:
- Correction #9: Model allowlist to prevent expensive/unsafe model abuse
- Default model selection per media_type
- Configurable sync vs queue mode per model
"""

from typing import Dict, Any, Optional


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
        "model": "fal-ai/kling-video/v1/standard/image-to-video",
        "mode": "queue",
        "timeout": 300,
        "description": "Convert image to video with Kling"
    },
    "video-generation": {
        "model": "fal-ai/runway-gen3/turbo/image-to-video",
        "mode": "queue",
        "timeout": 180,
        "description": "Generate video from image with Runway Gen-3"
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
    "fal-ai/flux-realism",
    
    # Video models
    "fal-ai/kling-video/v1/standard/image-to-video",
    "fal-ai/kling-video/v1/standard/text-to-video",
    "fal-ai/runway-gen3/turbo/image-to-video",
    "fal-ai/luma-dream-machine",
    
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
    return model in ALLOWED_MODELS


def list_media_types() -> list[str]:
    """List all supported media types"""
    return list(MEDIA_ROUTING_CONFIG.keys())


def list_allowed_models() -> list[str]:
    """List all allowed models"""
    return sorted(ALLOWED_MODELS)
