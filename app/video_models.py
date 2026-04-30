"""
OpenRouter video model catalogue.

Each entry maps a short model_key (used in API requests) to the full
provider model ID and metadata. The engine and frontend use model_key;
the gateway resolves it to model_id before calling the provider.

recommended=True marks models that are actively curated for MovieShaker use.

Selection strategy:
  kling-v3-pro  — default for most shots; best value, flexible i2v and t2v
  sora-2-pro    — scenes where character consistency across cuts matters
  veo-3-1       — hero shots; native audio generation makes it worth the cost
"""

from typing import Dict, Any

OPENROUTER_VIDEO_MODELS: Dict[str, Dict[str, Any]] = {
    "kling-v3-pro": {
        "model_id": "kling-ai/kling-video-v3-pro",
        "description": "Best value, flexible image-to-video and text-to-video",
        "recommended": True,
        "use_when": "default — most shots, scene previsualization, character blocking",
        "supports_image_to_video": True,
        "supports_text_to_video": True,
        "supports_native_audio": False,
        "max_duration_seconds": 10,
        "cost_per_second": 0.045,
    },
    "sora-2-pro": {
        "model_id": "openai/sora-2-pro",
        "description": "Best temporal consistency and camera motion control",
        "recommended": True,
        "use_when": "scenes where character consistency across cuts matters",
        "supports_image_to_video": True,
        "supports_text_to_video": True,
        "supports_native_audio": False,
        "max_duration_seconds": 20,
        "cost_per_second": 0.15,
    },
    "veo-3-1": {
        "model_id": "google/veo-3.1",
        "description": "Highest quality, native audio generation",
        "recommended": True,
        "use_when": "hero shots where native audio is needed",
        "supports_image_to_video": True,
        "supports_text_to_video": True,
        "supports_native_audio": True,
        "max_duration_seconds": 8,
        "cost_per_second": 0.12,
    },
    "wan-2-7": {
        "model_id": "wan-ai/wan-2.7",
        "description": "Open-weight model, good motion quality",
        "recommended": False,
        "use_when": "general purpose video clips",
        "supports_image_to_video": True,
        "supports_text_to_video": True,
        "supports_native_audio": False,
        "max_duration_seconds": 6,
        "cost_per_second": 0.02,
    },
    "seedance-2": {
        "model_id": "bytedance/seedance-2",
        "description": "Fast generation, good for iterative drafts",
        "recommended": False,
        "use_when": "quick draft video passes",
        "supports_image_to_video": True,
        "supports_text_to_video": False,
        "supports_native_audio": False,
        "max_duration_seconds": 5,
        "cost_per_second": 0.025,
    },
}

DEFAULT_VIDEO_MODEL = "kling-v3-pro"
RECOMMENDED_VIDEO_MODELS = [k for k, v in OPENROUTER_VIDEO_MODELS.items() if v["recommended"]]
