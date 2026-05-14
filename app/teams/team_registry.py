"""
Team registry for MovieShaker AI Team orchestration.

Four teams own the production workflow. Each team defines which tasks it
handles and its ranked model preferences per media type. The gateway uses
this registry to resolve which model executes a given (team, task) pair.

Teams never expose provider or model details externally.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class TeamDefinition:
    name: str
    display_name: str
    description: str
    capabilities: List[str]          # human-readable tags for what this team does
    text_models: List[str]           # ranked full OpenRouter model IDs for text tasks
    image_models: List[str]          # ranked model_keys for image tasks
    video_models: List[str]          # ranked model_keys for video tasks
    tasks: List[str]                 # task names this team handles
    fallback_team: Optional[str] = None   # team name to use if this team cannot resolve


TEAM_REGISTRY: Dict[str, TeamDefinition] = {

    "cowriter": TeamDefinition(
        name="cowriter",
        display_name="CoWriter Team",
        description=(
            "Script, dialogue, story development, scene analysis, "
            "festival strategy, funding, and marketing content"
        ),
        capabilities=[
            "screenplay",
            "dialogue",
            "scene-rewrite",
            "script-analysis",
            "shotlist-analysis",
            "festival-strategy",
            "funding-submission",
            "marketing",
            "documentary",
            "film-in-a-box",
        ],
        text_models=[
            "anthropic/claude-3.7-sonnet",
            "anthropic/claude-3-haiku",
            "google/gemma-3-12b-it",
        ],
        image_models=[],
        video_models=[],
        tasks=[
            "analyze-script",
            "analyze-shotlist",
            "festival-analysis",
            "funding-analysis",
            "marketing-analysis",
            "documentary-generation",
            "cowriter-text",
        ],
        fallback_team=None,
    ),

    "coproducer": TeamDefinition(
        name="coproducer",
        display_name="CoProducer Team",
        description=(
            "Production decisions, scheduling, budgeting, "
            "cast logistics, and location planning"
        ),
        capabilities=[
            "scheduling",
            "budgeting",
            "production-decisions",
            "cast-logistics",
            "location-planning",
            "shoot-day",
            "cost-analysis",
        ],
        text_models=[
            "google/gemma-3-12b-it",
            "anthropic/claude-3.7-sonnet",
            "openai/gpt-4.1-mini",
        ],
        image_models=[],
        video_models=[],
        tasks=[
            "production-decisions",
            "budget-analysis",
            "schedule-generation",
            "coproducer-text",
        ],
        fallback_team="cowriter",
    ),

    "codirector": TeamDefinition(
        name="codirector",
        display_name="CoDirector Team",
        description=(
            "Shot planning, scene visualization, camera direction, "
            "moodboard direction, and image-to-video generation"
        ),
        capabilities=[
            "shot-planning",
            "visualization",
            "camera-direction",
            "scene-composition",
            "moodboard",
            "tram-lines",
            "image-to-video",
            "cinematic-structure",
        ],
        text_models=[
            "anthropic/claude-3.7-sonnet",
            "google/gemma-3-12b-it",
        ],
        image_models=[
            "flux-2-pro",
            "flux-2-klein",
            "nano-banana-2",
        ],
        video_models=[
            "kling-v3-pro",
            "veo-3-1",
            "veo-3-1-fast",
            "hailuo-2-3",
            "wan-2-7",
        ],
        tasks=[
            "generate-shot",
            "generate-moodboard-sketch",
            "codirector-text",
        ],
        fallback_team="codesigner",
    ),

    "codesigner": TeamDefinition(
        name="codesigner",
        display_name="CoDesigner Team",
        description=(
            "Character images, backgrounds, props, visual identity, "
            "colour direction, and object generation"
        ),
        capabilities=[
            "character-generation",
            "background-generation",
            "prop-generation",
            "visual-identity",
            "colour-palette",
            "visual-continuity",
            "object-images",
            "moodboard-colour",
        ],
        text_models=[
            "anthropic/claude-3.7-sonnet",
            "google/gemma-3-12b-it",
        ],
        image_models=[
            "nano-banana-pro",
            "gpt-5-image",
            "nano-banana-2",
            "nano-banana",
            "flux-2-pro",
            "flux-2-klein",
        ],
        video_models=[],
        tasks=[
            "generate-image",
            "generate-character-image",
            "generate-background-image",
            "generate-sketch-image",
            "generate-moodboard-colour",
            "generate-moodboard-reference",
            "codesigner-text",
        ],
        fallback_team="codirector",
    ),
}
