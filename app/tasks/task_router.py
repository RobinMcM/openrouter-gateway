"""
Task resolver.

resolve_task() walks the ranked model list for a task and returns the first
model_key that exists in the live image or video catalogue.
"""

from typing import Optional
from app.tasks.task_registry import TASK_REGISTRY, TaskDefinition
from app.image_models import OPENROUTER_IMAGE_MODELS
from app.video_models import OPENROUTER_VIDEO_MODELS


def resolve_task(task_name: str) -> Optional[tuple[TaskDefinition, str]]:
    """
    Return (TaskDefinition, resolved_model_key) or None if task is unknown
    or no model in its ranked list is available.
    """
    task = TASK_REGISTRY.get(task_name)
    if task is None:
        return None

    catalogue = OPENROUTER_IMAGE_MODELS if task.endpoint == "image" else OPENROUTER_VIDEO_MODELS

    for model_key in task.models:
        if model_key in catalogue:
            return task, model_key

    return None
