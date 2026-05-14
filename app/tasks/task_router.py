"""
Task resolver.

resolve_task() walks the ranked model list for a task and returns the first
available model.

  text tasks:  models are full OpenRouter model IDs — always assumed available;
               return the first model in the list.
  image tasks: return first model_key present in OPENROUTER_IMAGE_MODELS.
  video tasks: return first model_key present in OPENROUTER_VIDEO_MODELS.
"""

from typing import Optional
from app.tasks.task_registry import TASK_REGISTRY, TaskDefinition
from app.image_models import OPENROUTER_IMAGE_MODELS
from app.video_models import OPENROUTER_VIDEO_MODELS


def resolve_task(task_name: str) -> Optional[tuple[TaskDefinition, str]]:
    """
    Return (TaskDefinition, resolved_model) or None if task is unknown
    or no model in its ranked list is available.
    """
    task = TASK_REGISTRY.get(task_name)
    if task is None:
        return None

    if task.endpoint == "text":
        if task.models:
            return task, task.models[0]
        return None

    catalogue = OPENROUTER_IMAGE_MODELS if task.endpoint == "image" else OPENROUTER_VIDEO_MODELS
    for model_key in task.models:
        if model_key in catalogue:
            return task, model_key

    return None
