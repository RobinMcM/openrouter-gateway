"""
Task catalogue.

Each task maps a caller-supplied task name to a ranked model list and a target
endpoint ("image", "video", or "text"). The gateway resolves the first model
that is available and dispatches to the appropriate handler.

  "image" / "video" tasks: models are model_key aliases (e.g. "flux-2-pro").
  "text" tasks:            models are full OpenRouter model IDs
                           (e.g. "anthropic/claude-3.7-sonnet").
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class TaskDefinition:
    description: str
    endpoint: str                          # "image" | "video" | "text"
    models: List[str]                      # ranked best-first
    default_options: Dict[str, Any] = field(default_factory=dict)


TASK_REGISTRY: Dict[str, TaskDefinition] = {

    # ── Video tasks ────────────────────────────────────────────────────────────

    "generate-shot": TaskDefinition(
        description="Generate a video shot from a source image (image-to-video)",
        endpoint="video",
        models=["kling-v3-pro", "sora-2-pro", "veo-3-1", "veo-3-1-fast", "hailuo-2-3"],
        default_options={"duration": 5, "aspect_ratio": "16:9"},
    ),

    # ── Image tasks ────────────────────────────────────────────────────────────

    "generate-image": TaskDefinition(
        description="Generate a still image from a text prompt",
        endpoint="image",
        models=["nano-banana-pro", "gpt-5-image", "nano-banana", "flux-2-pro"],
        default_options={},
    ),
    "generate-character-image": TaskDefinition(
        description="Generate or reference a character portrait image",
        endpoint="image",
        models=["nano-banana-2", "nano-banana-pro", "gpt-5-image", "flux-2-pro"],
        default_options={},
    ),
    "generate-background-image": TaskDefinition(
        description="Generate a scene background or environment image",
        endpoint="image",
        models=["nano-banana", "nano-banana-2", "flux-2-pro", "flux-2-klein"],
        default_options={},
    ),
    "generate-moodboard-sketch": TaskDefinition(
        description="Generate a sketch or rough gestural moodboard pass",
        endpoint="image",
        models=["flux-2-pro", "flux-2-klein"],
        default_options={},
    ),
    "generate-moodboard-colour": TaskDefinition(
        description="Generate a colour, tonal, or aesthetic moodboard pass",
        endpoint="image",
        models=["nano-banana-2", "nano-banana", "flux-2-pro"],
        default_options={},
    ),
    "generate-moodboard-reference": TaskDefinition(
        description="Generate a high-fidelity cinematic reference image",
        endpoint="image",
        models=["gpt-5-image", "nano-banana-pro", "nano-banana-2"],
        default_options={},
    ),
    "generate-sketch-image": TaskDefinition(
        description="Generate a hand-drawn sketch or storyboard frame",
        endpoint="image",
        models=["flux-2-pro", "flux-2-klein"],
        default_options={},
    ),

    # ── Text tasks — CoWriter ──────────────────────────────────────────────────

    "analyze-script": TaskDefinition(
        description="Analyse a screenplay for characters, scenes, and production elements",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "anthropic/claude-3-haiku"],
        default_options={"max_tokens": 8192},
    ),
    "analyze-shotlist": TaskDefinition(
        description="Analyse a scene and produce a shot list breakdown",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "anthropic/claude-3-haiku"],
        default_options={"max_tokens": 4096},
    ),
    "festival-analysis": TaskDefinition(
        description="Generate festival strategy and submission analysis",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "anthropic/claude-3-haiku"],
        default_options={"max_tokens": 4096},
    ),
    "funding-analysis": TaskDefinition(
        description="Generate funding strategy and application content",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "anthropic/claude-3-haiku"],
        default_options={"max_tokens": 4096},
    ),
    "marketing-analysis": TaskDefinition(
        description="Generate marketing and distribution strategy content",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "anthropic/claude-3-haiku"],
        default_options={"max_tokens": 4096},
    ),
    "documentary-generation": TaskDefinition(
        description="Generate documentary script or treatment content",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "anthropic/claude-3-haiku"],
        default_options={"max_tokens": 8192},
    ),
    "cowriter-text": TaskDefinition(
        description="General CoWriter text: script, story, dialogue, rewrites",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "anthropic/claude-3-haiku", "google/gemma-3-12b-it"],
        default_options={"max_tokens": 8192},
    ),

    # ── Text tasks — CoProducer ────────────────────────────────────────────────

    "production-decisions": TaskDefinition(
        description="Generate production logistics decisions and recommendations",
        endpoint="text",
        models=["google/gemma-3-12b-it", "anthropic/claude-3.7-sonnet"],
        default_options={"max_tokens": 4096},
    ),
    "budget-analysis": TaskDefinition(
        description="Analyse and recommend on production budget allocation",
        endpoint="text",
        models=["google/gemma-3-12b-it", "anthropic/claude-3.7-sonnet"],
        default_options={"max_tokens": 4096},
    ),
    "schedule-generation": TaskDefinition(
        description="Generate or optimise a shoot schedule",
        endpoint="text",
        models=["google/gemma-3-12b-it", "anthropic/claude-3.7-sonnet"],
        default_options={"max_tokens": 4096},
    ),
    "coproducer-text": TaskDefinition(
        description="General CoProducer text: scheduling, logistics, production planning",
        endpoint="text",
        models=["google/gemma-3-12b-it", "anthropic/claude-3.7-sonnet", "openai/gpt-4.1-mini"],
        default_options={"max_tokens": 4096},
    ),

    # ── Text tasks — CoDirector ────────────────────────────────────────────────

    "codirector-text": TaskDefinition(
        description="General CoDirector text: shot planning, camera direction, scene analysis",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "google/gemma-3-12b-it"],
        default_options={"max_tokens": 4096},
    ),

    # ── Text tasks — CoDesigner ────────────────────────────────────────────────

    "codesigner-text": TaskDefinition(
        description="General CoDesigner text: visual identity, design direction, colour",
        endpoint="text",
        models=["anthropic/claude-3.7-sonnet", "google/gemma-3-12b-it"],
        default_options={"max_tokens": 4096},
    ),
}
