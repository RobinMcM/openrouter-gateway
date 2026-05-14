from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


# ── Routing ──────────────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    job_type: str = Field(..., description="Job type: text-completion, etc.")
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Optional data for cost estimation")


class RouteResponse(BaseModel):
    status: str = "ok"
    routing: Dict[str, str]   # provider, model, endpoint
    estimate: Dict[str, Any]


# ── Execute (OpenRouter only) ─────────────────────────────────────────────────

class OpenRouterExecuteRequest(BaseModel):
    provider: Literal["openrouter"] = "openrouter"
    job_type: str
    payload: Dict[str, Any]
    dry_run: bool = False


class ExecuteResponse(BaseModel):
    """Synchronous execution response (OpenRouter)."""
    status: str = "ok"
    routing: dict
    result: Optional[dict] = None
    usage: dict


# ── Standard responses ────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    status: str = "ok"
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str


# ── API introspection ─────────────────────────────────────────────────────────

class EndpointInfo(BaseModel):
    name: str
    method: str
    path: str
    description: str
    request_body: Optional[Dict[str, Any]]
    success_response: Dict[str, Any]
    error_response: Optional[Dict[str, Any]]


class InstructionsResponse(BaseModel):
    status: str = "ok"
    service: str = "openrouter-gateway"
    auth: Dict[str, str] = Field(default_factory=lambda: {"header": "X-Internal-API-Key"})
    endpoints: List[EndpointInfo]


class LogsResponse(BaseModel):
    status: str = "ok"
    lines: int
    logs: List[str]


# ── Config management ─────────────────────────────────────────────────────────

class UpdateOpenRouterKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=10, description="OpenRouter API key (sk-or-v1-...)")


class TestOpenRouterKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=10, description="OpenRouter API key to test")


class TestOpenRouterKeyResponse(BaseModel):
    status: str
    valid: bool
    message: str


class OpenRouterKeyStatusResponse(BaseModel):
    status: str = "ok"
    configured: bool
    message: str


# ── Models showcase ───────────────────────────────────────────────────────────

class ShowcaseModel(BaseModel):
    id: str
    name: str
    provider: str
    best_for: List[str]
    strengths: List[str]
    limitations: List[str]
    output_specs: str
    estimated_cost: str
    use_cases: List[str]


class ShowcaseCategory(BaseModel):
    title: str
    icon: str
    description: str
    models: List[ShowcaseModel]


class ModelsShowcaseResponse(BaseModel):
    status: str = "ok"
    categories: Dict[str, ShowcaseCategory]


# ── Agent classifier ──────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    message: str
    context_mode: str   # "scripts" | "scheduling" | "shotlist" | "moodboard" | "budgets" | "general"
    page_path: str = ""


class ClassifyResponse(BaseModel):
    agent: str          # "cowriter" | "coproducer" | "codirector" | "codesigner"
    confidence: float
    reasoning: str


# ── Image generation (OpenRouter synchronous) ─────────────────────────────────

class ImageGenerateRequest(BaseModel):
    prompt: str
    model_key: str = "flux-2-klein"
    aspect_ratio: str = "1:1"
    dry_run: bool = False


class ImageGenerateResponse(BaseModel):
    ok: bool
    image_b64: Optional[str] = None
    content_type: str = "image/png"
    model: str
    model_key: str
    dry_run: bool = False


# ── Video generation (OpenRouter synchronous) ─────────────────────────────────

class VideoGenerateRequest(BaseModel):
    prompt: str
    model_key: str = "kling-v3-pro"
    source_image: Optional[str] = None   # URL for image-to-video
    duration: int = 5                    # seconds
    aspect_ratio: str = "16:9"
    dry_run: bool = False


class VideoGenerateResponse(BaseModel):
    ok: bool
    video_url: Optional[str] = None      # URL to generated video
    content_type: str = "video/mp4"
    model: str
    model_key: str
    dry_run: bool = False


# ── Task dispatch ─────────────────────────────────────────────────────────────

class TaskExecuteRequest(BaseModel):
    task: str
    source: Optional[str] = None         # image/video URL
    prompt: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class TaskExecuteResponse(BaseModel):
    ok: bool
    task: str
    resolved_model: str
    endpoint: str                        # "image", "video", or "text"
    dry_run: bool = False
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ── Team routing ──────────────────────────────────────────────────────────────

class TeamRouteRequest(BaseModel):
    team: str
    task: str


class TeamRouteResponse(BaseModel):
    ok: bool
    team: str
    team_display_name: str
    task: str
    resolved_model: str
    endpoint: str                        # "text" | "image" | "video"
    error: Optional[str] = None


class TeamExecuteRequest(BaseModel):
    team: str
    task: str
    source: Optional[str] = None         # image/video URL for media tasks
    prompt: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None   # for text tasks
    options: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class TeamExecuteResponse(BaseModel):
    ok: bool
    team: str
    task: str
    resolved_model: str
    endpoint: str
    dry_run: bool = False
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
