"""
Team routing logic.

resolve_team_task() walks the (team, task) combination and returns the first
available model, falling back through the team's fallback_team chain if needed.

For text tasks: the returned model is a full OpenRouter model ID.
For image tasks: the returned model is a model_key from OPENROUTER_IMAGE_MODELS.
For video tasks: the returned model is a model_key from OPENROUTER_VIDEO_MODELS.
"""

from typing import Optional
from app.teams.team_registry import TEAM_REGISTRY, TeamDefinition
from app.tasks.task_registry import TASK_REGISTRY, TaskDefinition
from app.image_models import OPENROUTER_IMAGE_MODELS
from app.video_models import OPENROUTER_VIDEO_MODELS


def resolve_team_task(
    team_name: str,
    task_name: str,
    *,
    _visited: frozenset = frozenset(),
) -> Optional[tuple[TeamDefinition, TaskDefinition, str]]:
    """
    Resolve (team_name, task_name) to (TeamDefinition, TaskDefinition, model).

    Resolution strategy:
    1. For text tasks: return first model from team.text_models (always available).
    2. For image tasks: intersect team.image_models with OPENROUTER_IMAGE_MODELS catalogue;
       fall back to task.models if team has no image models.
    3. For video tasks: same pattern with team.video_models and OPENROUTER_VIDEO_MODELS.
    4. If no model resolves: walk team.fallback_team chain (cycle-safe via _visited).
    5. Return None if nothing resolves.
    """
    if team_name in _visited:
        return None

    team = TEAM_REGISTRY.get(team_name)
    if team is None:
        return None

    task = TASK_REGISTRY.get(task_name)
    if task is None:
        return None

    if task.endpoint == "text":
        if team.text_models:
            return team, task, team.text_models[0]

    elif task.endpoint == "image":
        # Team's preferred image models take priority; fall back to task's own list.
        if team.image_models:
            candidates = [m for m in team.image_models if m in OPENROUTER_IMAGE_MODELS]
        else:
            candidates = [m for m in task.models if m in OPENROUTER_IMAGE_MODELS]
        if candidates:
            return team, task, candidates[0]

    elif task.endpoint == "video":
        if team.video_models:
            candidates = [m for m in team.video_models if m in OPENROUTER_VIDEO_MODELS]
        else:
            candidates = [m for m in task.models if m in OPENROUTER_VIDEO_MODELS]
        if candidates:
            return team, task, candidates[0]

    # Nothing resolved on this team — walk fallback chain.
    if team.fallback_team and team.fallback_team not in _visited:
        return resolve_team_task(
            team.fallback_team,
            task_name,
            _visited=_visited | {team_name},
        )

    return None
