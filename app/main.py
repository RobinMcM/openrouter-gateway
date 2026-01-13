from fastapi import FastAPI, Depends
import uuid
from app.auth import verify_api_key
from app.schemas import (
    RouteRequest, RouteResponse, ExecuteRequest, ExecuteResponse,
    ErrorResponse, InstructionsResponse, EndpointInfo, LogsResponse
)
from app.logger import get_sanitized_logs, log_request, log_success, log_error
from app.config import ROUTING_CONFIG
from app.openrouter_client import (
    calculate_cost_estimate, call_openrouter, extract_actual_usage
)

app = FastAPI(title="OpenRouter Gateway", version="1.0.0")


@app.get("/health")
async def health_check():
    """
    Unauthenticated health check endpoint.
    Used by monitoring systems to verify service is running.
    """
    return {"status": "healthy"}


@app.get("/api/instructions", response_model=InstructionsResponse)
async def get_instructions(api_key: str = Depends(verify_api_key)):
    """
    Get API documentation for all endpoints.
    Returns instructions for using the OpenRouter Gateway API.
    """
    endpoints = [
        EndpointInfo(
            name="health",
            method="GET",
            path="/health",
            description="Unauthenticated health check for monitoring",
            request_body=None,
            success_response={"status": "healthy"},
            error_response=None
        ),
        EndpointInfo(
            name="instructions",
            method="GET",
            path="/api/instructions",
            description="Get API documentation and endpoint information",
            request_body=None,
            success_response={
                "status": "ok",
                "service": "openrouter-gateway",
                "endpoints": "[...]"
            },
            error_response={"status": "error", "message": "Error description"}
        ),
        EndpointInfo(
            name="logs",
            method="GET",
            path="/api/logs?lines=200",
            description="Get recent operational logs (sanitized)",
            request_body=None,
            success_response={
                "status": "ok",
                "lines": 200,
                "logs": ["log line 1", "log line 2"]
            },
            error_response={"status": "error", "message": "Error description"}
        ),
        EndpointInfo(
            name="route",
            method="POST",
            path="/api/route",
            description="Get routing decision and cost estimate (does NOT call OpenRouter)",
            request_body={
                "job_type": "text-completion",
                "input_data": {
                    "prompt": "Hello, how are you?",
                    "max_tokens": 100
                }
            },
            success_response={
                "status": "ok",
                "routing": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "endpoint": "/chat/completions"
                },
                "estimate": {
                    "input_tokens": 5,
                    "output_tokens": 100,
                    "input_cost": 0.00015,
                    "output_cost": 0.006,
                    "subtotal": 0.00615,
                    "admin_markup_percent": 0.10,
                    "admin_markup_fixed": 0.001,
                    "admin_total": 0.001615,
                    "total": 0.007765,
                    "estimated": True
                }
            },
            error_response={"status": "error", "message": "Unknown job_type"}
        ),
        EndpointInfo(
            name="execute",
            method="POST",
            path="/api/execute",
            description="Execute OpenRouter API call or dry-run with cost tracking",
            request_body={
                "job_type": "text-completion",
                "payload": {
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": "Hello!"}]
                },
                "dry_run": False
            },
            success_response={
                "status": "ok",
                "routing": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "endpoint": "/chat/completions"
                },
                "result": {"choices": [{"message": {"content": "Hello there!"}}]},
                "usage": {
                    "input_tokens": 8,
                    "output_tokens": 5,
                    "total_cost": 0.00054,
                    "estimated": False
                }
            },
            error_response={"status": "error", "message": "Error description"}
        )
    ]
    
    return InstructionsResponse(endpoints=endpoints)


@app.get("/api/logs", response_model=LogsResponse)
async def get_logs(
    lines: int = 200,
    api_key: str = Depends(verify_api_key)
):
    """
    Get recent operational logs for debugging.
    Returns the last N lines from the log file (default 200, max 1000).
    All sensitive data is redacted before returning.
    """
    # Validate and cap lines parameter
    if lines > 1000:
        lines = 1000
    if lines < 1:
        lines = 1
    
    # Get sanitized logs
    logs = get_sanitized_logs(lines)
    
    return LogsResponse(lines=len(logs), logs=logs)


@app.post("/api/route", response_model=RouteResponse | ErrorResponse)
async def route_request(
    request: RouteRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Get routing decision and cost estimate for a job type.
    This endpoint NEVER calls OpenRouter - it only returns routing info and estimates.
    """
    job_id = str(uuid.uuid4())
    log_request("route", job_id)
    
    try:
        # Look up routing for job_type
        job_type = request.job_type
        
        if job_type not in ROUTING_CONFIG:
            log_error(job_id, f"Unknown job_type: {job_type}")
            return ErrorResponse(message=f"Unknown job_type: {job_type}")
        
        routing = ROUTING_CONFIG[job_type]
        
        # Calculate cost estimate
        estimate = calculate_cost_estimate(routing, request.input_data)
        
        log_success(job_id, f"job_type={job_type} model={routing.get('model')}")
        
        return RouteResponse(
            routing=routing,
            estimate=estimate
        )
    
    except Exception as e:
        log_error(job_id, str(e))
        return ErrorResponse(message=f"Unexpected error: {str(e)}")


@app.post("/api/execute", response_model=ExecuteResponse | ErrorResponse)
async def execute_request(
    request: ExecuteRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Execute OpenRouter API call or dry-run with cost tracking.
    
    If dry_run=true: Returns routing + estimate only (no OpenRouter call)
    If dry_run=false: Makes actual OpenRouter API call and returns result + usage
    """
    job_id = str(uuid.uuid4())
    log_request("execute", job_id)
    
    try:
        # Look up routing for job_type
        job_type = request.job_type
        
        if job_type not in ROUTING_CONFIG:
            log_error(job_id, f"Unknown job_type: {job_type}")
            return ErrorResponse(message=f"Unknown job_type: {job_type}")
        
        routing = ROUTING_CONFIG[job_type]
        
        # Dry run - return estimate only
        if request.dry_run:
            estimate = calculate_cost_estimate(routing, request.payload)
            log_success(job_id, f"dry_run=true job_type={job_type}")
            
            return ExecuteResponse(
                routing=routing,
                result=None,
                usage=estimate
            )
        
        # Execute actual OpenRouter call
        endpoint = routing.get("endpoint", "/chat/completions")
        success, response_data, error_msg = await call_openrouter(endpoint, request.payload)
        
        if not success:
            log_error(job_id, error_msg or "Unknown error")
            return ErrorResponse(message=error_msg or "OpenRouter API call failed")
        
        # Extract actual usage from response
        usage = extract_actual_usage(response_data, routing)
        
        log_success(job_id, f"job_type={job_type} model={routing.get('model')} estimated={usage.get('estimated', True)}")
        
        return ExecuteResponse(
            routing=routing,
            result=response_data,
            usage=usage
        )
    
    except Exception as e:
        log_error(job_id, str(e))
        return ErrorResponse(message=f"Unexpected error: {str(e)}")
