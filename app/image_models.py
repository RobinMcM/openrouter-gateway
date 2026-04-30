"""
OpenRouter image model catalogue.

Each entry maps a short model_key (used in API requests) to the full
OpenRouter model ID and metadata. The engine and frontend use model_key;
the gateway resolves it to model_id before calling OpenRouter.
"""

from typing import Dict, Any

OPENROUTER_IMAGE_MODELS: Dict[str, Dict[str, Any]] = {
    "flux-2-pro": {
        "model_id": "black-forest-labs/flux.2-pro",
        "description": "High quality, best prompt adherence",
        "supports_aspect_ratio": False,
        "cost_per_mp": 0.03,
        "best_for": "moodboard cinematic passes",
    },
    "flux-2-flex": {
        "model_id": "black-forest-labs/flux.2-flex",
        "description": "Text rendering, multi-reference editing",
        "supports_aspect_ratio": False,
        "cost_per_mp": 0.06,
        "best_for": "artifacts with text, inserts",
    },
    "flux-2-klein": {
        "model_id": "black-forest-labs/flux.2-klein",
        "description": "Fastest and cheapest FLUX",
        "supports_aspect_ratio": False,
        "cost_per_mp": 0.014,
        "best_for": "pencil sketches, drafts",
    },
    "nano-banana": {
        "model_id": "google/gemini-2.5-flash-image-preview",
        "description": "Fast, contextual, good quality",
        "supports_aspect_ratio": True,
        "cost_per_image": 0.04,
        "best_for": "backgrounds, scene objects",
    },
    "nano-banana-2": {
        "model_id": "google/gemini-3.1-flash-image-preview",
        "description": "Pro quality at flash speed",
        "supports_aspect_ratio": True,
        "cost_per_image": 0.07,
        "best_for": "character references",
    },
    "seedream-4-5": {
        "model_id": "bytedance/seedream-4.5",
        "description": "Fast, good portraits",
        "supports_aspect_ratio": False,
        "cost_per_image": 0.04,
        "best_for": "character generation",
    },
    "gpt-5-image": {
        "model_id": "openai/gpt-5-image",
        "description": "Highest quality, best text rendering",
        "supports_aspect_ratio": False,
        "cost_varies": True,
        "best_for": "final reference shots",
    },
}

DEFAULT_IMAGE_MODEL = "flux-2-pro"
