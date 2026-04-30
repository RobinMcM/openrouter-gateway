from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal, Annotated


# Request/Response schemas for routing endpoint
class RouteRequest(BaseModel):
    job_type: str
    input_data: dict = {}  # For estimation hints (e.g., prompt text, image count)


class RouteResponse(BaseModel):
    status: str = "ok"
    routing: dict  # {provider, model, endpoint}
    estimate: dict  # cost breakdown


# Request/response schemas for execute endpoint (with provider discriminator)
class BaseExecuteRequest(BaseModel):
    """Base class with provider discriminator"""
    provider: str

class OpenRouterExecuteRequest(BaseExecuteRequest):
    """OpenRouter-specific execute request"""
    provider: Literal["openrouter"] = "openrouter"
    job_type: str
    payload: Dict[str, Any]
    dry_run: bool = False

class FalExecuteRequest(BaseExecuteRequest):
    """FAL.ai-specific execute request"""
    provider: Literal["fal"] = "fal"
    media_type: str  # "image-generation", "video-generation", etc.
    model: Optional[str] = None  # Override default model for media_type
    payload: Dict[str, Any]
    dry_run: bool = False
    webhook_url: Optional[str] = None  # For async notifications

# Discriminated union - Pydantic will route based on provider field
ExecuteRequest = Annotated[
    Union[OpenRouterExecuteRequest, FalExecuteRequest],
    Field(discriminator="provider")
]

class ExecuteResponse(BaseModel):
    """Immediate response for sync execution (OpenRouter)"""
    status: str = "ok"
    routing: dict
    result: Optional[dict] = None  # OpenRouter response if executed
    usage: dict  # actual or estimated usage/cost

class AsyncJobResponse(BaseModel):
    """Response for async job submission (FAL)"""
    ok: bool = True
    job_id: str
    job_status: Literal["queued", "processing", "completed", "failed"]
    status_url: str
    estimate: Dict[str, Any]  # Cost estimate


# Generic media contract (final stabilization)
class GenericExecuteDestination(BaseModel):
    target: Optional[str] = Field(default=None, description="Destination target, e.g. digitalocean-spaces")
    bucket: Optional[str] = None
    path_prefix: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GenericExecuteRequest(BaseModel):
    provider: Literal["fal"] = "fal"
    query_type: Literal["text", "text-image", "image-video", "text-music"]
    model: str
    source_image: Optional[str] = Field(default=None, description="Source image URL/path for image-video jobs")
    destination: Optional[GenericExecuteDestination] = None
    options: Dict[str, Any] = Field(default_factory=dict, description="Generic options from caller")
    dry_run: bool = False
    webhook_url: Optional[str] = None


class GenericExecuteResponse(BaseModel):
    status: str = "ok"
    provider: str = "fal"
    query_type: str
    model: str
    canonical_model: str
    media_type: str
    accepted_fields: List[str] = Field(default_factory=list)
    defaulted_fields: Dict[str, Any] = Field(default_factory=dict)
    dropped_fields: List[str] = Field(default_factory=list)
    provider_request: Dict[str, Any] = Field(default_factory=dict)
    destination: Dict[str, Any] = Field(default_factory=dict)
    stage: str
    stage_history: List[str] = Field(default_factory=list)
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    status_url: Optional[str] = None
    estimate: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Standard response schemas matching ffmpeg-api pattern
class SuccessResponse(BaseModel):
    status: str = "ok"
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str


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


# OpenRouter Gateway specific schemas
class RouteRequest(BaseModel):
    job_type: str = Field(..., description="Job type: text-completion, image-generation, video-generation, etc.")
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Optional data for cost estimation")


class RouteResponse(BaseModel):
    status: str = "ok"
    routing: Dict[str, str]  # provider, model, endpoint
    estimate: Dict[str, Any]


# OLD ExecuteRequest class removed - now using discriminated union above (line 39)
# class ExecuteRequest(BaseModel):
#     job_type: str
#     payload: Dict[str, Any]  # OpenRouter API payload
#     dry_run: bool = False


# OLD ExecuteResponse class removed - now using ExecuteResponse/AsyncJobResponse above
# class ExecuteResponse(BaseModel):
#     status: str = "ok"
#     routing: Dict[str, str]
#     result: Optional[Dict[str, Any]] = None  # OpenRouter response if executed
#     usage: Dict[str, Any]  # actual or estimated usage/cost


# Models listing schemas
class ModelInfo(BaseModel):
    id: str
    name: str
    provider: Optional[str] = None


class ModelsResponse(BaseModel):
    status: str = "ok"
    models: List[ModelInfo]


# Configuration management schemas
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


# MovieShaker showcase schemas
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


# FAL job status schemas
class JobStatusResponse(BaseModel):
    """Response for /api/status/{job_id}"""
    ok: bool
    job_id: str
    job_status: Literal["queued", "processing", "completed", "failed"]
    provider_status: Optional[Dict[str, Any]] = None  # Raw provider status
    result: Optional[Dict[str, Any]] = None  # Files, metadata when completed
    usage: Optional[Dict[str, Any]] = None  # Cost info when completed
    error: Optional[str] = None  # Error message when failed
    warning: Optional[str] = None  # Transient errors
    stage: Optional[str] = None
    stage_history: Optional[List[str]] = None
    destination: Optional[Dict[str, Any]] = None


# Agent classifier schemas
class ClassifyRequest(BaseModel):
    message: str
    context_mode: str  # "scripts" | "scheduling" | "shotlist" | "moodboard" | "budgets" | "general"
    page_path: str = ""  # current URL path for extra context


class ClassifyResponse(BaseModel):
    agent: str  # "cowriter" | "coproducer" | "codirector"
    confidence: float  # 0.0 to 1.0
    reasoning: str  # one sentence why


# OpenRouter synchronous image generation schemas
class ImageGenerateRequest(BaseModel):
    prompt: str
    model_key: str = "flux-2-klein"
    aspect_ratio: str = "1:1"
    dry_run: bool = False


class ImageGenerateResponse(BaseModel):
    ok: bool
    image_b64: Optional[str] = None   # base64-encoded image; None on dry_run
    content_type: str = "image/png"
    model: str                        # full OpenRouter model ID
    model_key: str                    # short key from OPENROUTER_IMAGE_MODELS
    dry_run: bool = False
