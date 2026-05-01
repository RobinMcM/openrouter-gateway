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
        "best_for": "moodboard cinematic passes",
    },
    "flux-2-flex": {
        "model_id": "black-forest-labs/flux.2-flex",
        "description": "Text rendering, multi-reference",
        "supports_aspect_ratio": False,
        "best_for": "artifacts with text, inserts",
    },
    "flux-2-klein": {
        "model_id": "black-forest-labs/flux.2-klein",
        "description": "Fastest and cheapest FLUX",
        "supports_aspect_ratio": False,
        "best_for": "quick drafts",
    },
    "nano-banana": {
        "model_id": "google/gemini-2.5-flash-image",
        "description": "Fast, contextual, good quality",
        "supports_aspect_ratio": True,
        "best_for": "backgrounds, scene objects",
    },
    "nano-banana-2": {
        "model_id": "google/gemini-3.1-flash-image-preview",
        "description": "Pro quality at flash speed",
        "supports_aspect_ratio": True,
        "best_for": "character references",
    },
    "nano-banana-pro": {
        "model_id": "google/gemini-3-pro-image-preview",
        "description": "Most advanced Gemini image model",
        "supports_aspect_ratio": True,
        "best_for": "final quality images",
    },
    "gpt-5-image": {
        "model_id": "openai/gpt-5-image",
        "description": "Highest quality, best text rendering",
        "supports_aspect_ratio": False,
        "best_for": "final reference shots for Visualize",
    },
    "gpt-5-image-mini": {
        "model_id": "openai/gpt-5-image-mini",
        "description": "Fast GPT-5 image generation",
        "supports_aspect_ratio": False,
        "best_for": "quick high quality previews",
    },
    "gpt-5-4-image": {
        "model_id": "openai/gpt-5.4-image-2",
        "description": "Latest GPT image model",
        "supports_aspect_ratio": False,
        "best_for": "highest fidelity reference shots",
    },
}

DEFAULT_IMAGE_MODEL = "flux-2-pro"
