"""
Task catalogue.

Each task maps a caller-supplied task name to a ranked model list and a target
endpoint ("image" or "video"). The gateway resolves the first model_key that
is present in the live model catalogue and dispatches to the appropriate handler.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class TaskDefinition:
    description: str
    endpoint: str                          # "image" | "video"
    models: List[str]                      # ranked best-first (model_key values)
    default_options: Dict[str, Any] = field(default_factory=dict)


TASK_REGISTRY: Dict[str, TaskDefinition] = {
    "generate-shot": TaskDefinition(
        description="Generate a video shot from a text prompt or source image",
        endpoint="video",
        models=["kling-v3-pro", "sora-2-pro", "veo-3-1", "veo-3-1-fast", "hailuo-2-3"],
        default_options={"duration": 5, "aspect_ratio": "16:9"},
    ),
    "generate-image": TaskDefinition(
        description="Generate a still image from a text prompt",
        endpoint="image",
        models=["nano-banana-pro", "gpt-5-image", "nano-banana", "flux-2-pro"],
        default_options={},
    ),
}
