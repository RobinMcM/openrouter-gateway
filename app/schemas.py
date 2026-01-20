from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pydantic import field_validator


# Request/Response schemas for routing endpoint
class RouteRequest(BaseModel):
    job_type: str
    input_data: dict = {}  # For estimation hints (e.g., prompt text, image count)


class RouteResponse(BaseModel):
    status: str = "ok"
    routing: dict  # {provider, model, endpoint}
    estimate: dict  # cost breakdown


# Request/response schemas for execute endpoint
class ExecuteRequest(BaseModel):
    job_type: str
    payload: dict  # OpenRouter API payload
    dry_run: bool = False


class ExecuteResponse(BaseModel):
    status: str = "ok"
    routing: dict
    result: Optional[dict] = None  # OpenRouter response if executed
    usage: dict  # actual or estimated usage/cost


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


class ExecuteRequest(BaseModel):
    job_type: str
    payload: Dict[str, Any]  # OpenRouter API payload
    dry_run: bool = False


class ExecuteResponse(BaseModel):
    status: str = "ok"
    routing: Dict[str, str]
    result: Optional[Dict[str, Any]] = None  # OpenRouter response if executed
    usage: Dict[str, Any]  # actual or estimated usage/cost


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
