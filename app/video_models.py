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
        "model_id": "kwaivgi/kling-v3.0-pro",
        "description": "Premium quality, 3-15s clips",
        "max_duration": 15,
        "min_duration": 3,
        "aspect_ratios": ["16:9", "9:16", "1:1"],
        "supports_image_to_video": True,
        "supports_last_frame": True,
        "supports_reference_images": True,
        "supports_native_audio": True,
        "cost_per_second": 0.168,
        "recommended": True,
        "use_when": "Standard shots, dialogue scenes",
    },
    "sora-2-pro": {
        "model_id": "openai/sora-2-pro",
        "description": "Best consistency across cuts",
        "max_duration": 20,
        "min_duration": 5,
        "aspect_ratios": ["16:9", "9:16", "1:1"],
        "supports_image_to_video": True,
        "supports_last_frame": True,
        "supports_reference_images": False,
        "supports_native_audio": True,
        "cost_per_second": 0.30,
        "recommended": True,
        "use_when": "Multi-shot sequences, character consistency",
    },
    "veo-3-1": {
        "model_id": "google/veo-3.1",
        "description": "1080p, native audio, scene extension",
        "max_duration": 30,
        "min_duration": 5,
        "aspect_ratios": ["16:9", "9:16"],
        "supports_image_to_video": True,
        "supports_last_frame": True,
        "supports_reference_images": False,
        "supports_native_audio": True,
        "cost_per_second": 0.40,
        "recommended": True,
        "use_when": "Hero shots, scenes needing audio",
    },
    "veo-3-1-fast": {
        "model_id": "google/veo-3.1-fast",
        "description": "Faster Veo at lower cost",
        "max_duration": 30,
        "min_duration": 5,
        "aspect_ratios": ["16:9", "9:16"],
        "supports_image_to_video": True,
        "supports_last_frame": True,
        "supports_reference_images": False,
        "supports_native_audio": True,
        "cost_per_second": 0.20,
        "recommended": False,
        "use_when": "Draft video passes",
    },
    "hailuo-2-3": {
        "model_id": "minimax/hailuo-2.3",
        "description": "Realistic motion, character animation",
        "max_duration": 10,
        "min_duration": 3,
        "aspect_ratios": ["16:9", "9:16", "1:1"],
        "supports_image_to_video": True,
        "supports_last_frame": False,
        "supports_reference_images": True,
        "supports_native_audio": False,
        "cost_per_second": 0.15,
        "recommended": False,
        "use_when": "Character animation, expressive rendering",
    },
    "wan-2-7": {
        "model_id": "alibaba/wan-2.7",
        "description": "Open source, reference-to-video",
        "max_duration": 10,
        "min_duration": 3,
        "aspect_ratios": ["16:9", "9:16", "1:1"],
        "supports_image_to_video": True,
        "supports_last_frame": True,
        "supports_reference_images": True,
        "supports_native_audio": False,
        "cost_per_second": 0.08,
        "recommended": False,
        "use_when": "Budget shots, reference-guided generation",
    },
    "seedance-2": {
        "model_id": "bytedance/seedance-2.0",
        "description": "Fast generation, multimodal reference",
        "max_duration": 10,
        "min_duration": 3,
        "aspect_ratios": ["16:9", "9:16", "1:1"],
        "supports_image_to_video": True,
        "supports_last_frame": True,
        "supports_reference_images": True,
        "supports_native_audio": False,
        "cost_per_second": 0.10,
        "recommended": False,
        "use_when": "Fast iteration, draft video",
    },
    "kling-video-o1": {
        "model_id": "kwaivgi/kling-video-o1",
        "description": "Cinematic content, precise composition",
        "max_duration": 10,
        "min_duration": 5,
        "aspect_ratios": ["16:9", "9:16", "1:1"],
        "supports_image_to_video": True,
        "supports_last_frame": True,
        "supports_reference_images": False,
        "supports_native_audio": False,
        "cost_per_second": 0.20,
        "recommended": False,
        "use_when": "Precise scene composition control",
    },
}

DEFAULT_VIDEO_MODEL = "kling-v3-pro"
RECOMMENDED_VIDEO_MODELS = [k for k, v in OPENROUTER_VIDEO_MODELS.items() if v.get("recommended")]
