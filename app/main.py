from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
import uuid
from app.auth import verify_api_key
from app.schemas import (
    RouteRequest, RouteResponse, ExecuteRequest, ExecuteResponse,
    ErrorResponse, InstructionsResponse, EndpointInfo, LogsResponse,
    ModelsResponse, ModelInfo
)
from app.models_data import OPENROUTER_MODELS
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


@app.get("/api/models", response_model=ModelsResponse)
async def get_models(api_key: str = Depends(verify_api_key)):
    """
    Get list of available OpenRouter models.
    Returns a static list of popular models with basic information.
    No external API calls - data is hardcoded from OpenRouter's public website.
    """
    models = [ModelInfo(**model) for model in OPENROUTER_MODELS]
    return ModelsResponse(models=models)


@app.get("/models", response_class=HTMLResponse)
async def models_page():
    """
    HTML page for browsing OpenRouter models.
    Features a searchable dropdown and displays model overview when selected.
    Does not require authentication - public facing page.
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenRouter Models - Gateway</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .content {
            padding: 30px;
        }
        
        .search-section {
            margin-bottom: 30px;
        }
        
        label {
            display: block;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }
        
        #modelSearch {
            width: 100%;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        #modelSearch:focus {
            border-color: #667eea;
        }
        
        #modelSelect {
            width: 100%;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            outline: none;
            margin-top: 10px;
            cursor: pointer;
            transition: border-color 0.3s;
        }
        
        #modelSelect:focus {
            border-color: #667eea;
        }
        
        .overview-section {
            display: none;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }
        
        .overview-section.active {
            display: block;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .overview-section h2 {
            color: #667eea;
            font-size: 20px;
            margin-bottom: 15px;
        }
        
        .info-row {
            margin-bottom: 12px;
            display: flex;
            align-items: baseline;
        }
        
        .info-label {
            font-weight: 600;
            color: #555;
            min-width: 100px;
        }
        
        .info-value {
            color: #333;
            word-break: break-all;
        }
        
        .badge {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .error {
            background: #fee;
            border-left: 4px solid #f44;
            padding: 15px;
            border-radius: 4px;
            color: #c00;
            margin-bottom: 20px;
        }
        
        .count {
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 OpenRouter Models</h1>
            <p>Browse and explore available AI models</p>
        </div>
        
        <div class="content">
            <div id="errorMessage" class="error" style="display: none;"></div>
            
            <div class="search-section">
                <label for="modelSearch">Search Models</label>
                <input type="text" id="modelSearch" placeholder="Type to search models..." />
                
                <label for="modelSelect" style="margin-top: 20px;">Select a Model</label>
                <select id="modelSelect" size="10">
                    <option value="">Loading models...</option>
                </select>
                
                <div class="count" id="modelCount"></div>
            </div>
            
            <div id="modelOverview" class="overview-section">
                <h2>Model Overview</h2>
                <div class="info-row">
                    <span class="info-label">Model ID:</span>
                    <span class="info-value" id="modelId"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Name:</span>
                    <span class="info-value" id="modelName"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Provider:</span>
                    <span class="info-value"><span class="badge" id="modelProvider"></span></span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let allModels = [];
        let filteredModels = [];
        
        const searchInput = document.getElementById('modelSearch');
        const selectElement = document.getElementById('modelSelect');
        const overviewSection = document.getElementById('modelOverview');
        const errorMessage = document.getElementById('errorMessage');
        const modelCount = document.getElementById('modelCount');
        
        // Fetch models from API on page load
        async function fetchModels() {
            try {
                // Prompt for API key
                const apiKey = prompt('Please enter your API key (X-Internal-API-Key):');
                if (!apiKey) {
                    showError('API key is required to view models.');
                    return;
                }
                
                const response = await fetch('/api/models', {
                    headers: {
                        'X-Internal-API-Key': apiKey
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                allModels = data.models || [];
                filteredModels = [...allModels];
                
                populateSelect(filteredModels);
                updateCount();
                
            } catch (error) {
                showError('Failed to load models: ' + error.message);
            }
        }
        
        // Populate select element with models
        function populateSelect(models) {
            selectElement.innerHTML = '';
            
            if (models.length === 0) {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No models found';
                selectElement.appendChild(option);
                return;
            }
            
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = `${model.name} (${model.provider})`;
                option.dataset.model = JSON.stringify(model);
                selectElement.appendChild(option);
            });
        }
        
        // Filter models based on search input
        function filterModels() {
            const query = searchInput.value.toLowerCase();
            
            if (!query) {
                filteredModels = [...allModels];
            } else {
                filteredModels = allModels.filter(model => 
                    model.name.toLowerCase().includes(query) ||
                    model.id.toLowerCase().includes(query) ||
                    (model.provider && model.provider.toLowerCase().includes(query))
                );
            }
            
            populateSelect(filteredModels);
            updateCount();
        }
        
        // Display model overview
        function displayModelOverview() {
            const selectedOption = selectElement.options[selectElement.selectedIndex];
            
            if (!selectedOption || !selectedOption.value) {
                overviewSection.classList.remove('active');
                return;
            }
            
            const model = JSON.parse(selectedOption.dataset.model);
            
            document.getElementById('modelId').textContent = model.id;
            document.getElementById('modelName').textContent = model.name;
            document.getElementById('modelProvider').textContent = model.provider || 'N/A';
            
            overviewSection.classList.add('active');
        }
        
        // Show error message
        function showError(message) {
            errorMessage.textContent = message;
            errorMessage.style.display = 'block';
        }
        
        // Update model count display
        function updateCount() {
            if (allModels.length === 0) {
                modelCount.textContent = '';
            } else if (filteredModels.length === allModels.length) {
                modelCount.textContent = `Showing all ${allModels.length} models`;
            } else {
                modelCount.textContent = `Showing ${filteredModels.length} of ${allModels.length} models`;
            }
        }
        
        // Event listeners
        searchInput.addEventListener('input', filterModels);
        selectElement.addEventListener('change', displayModelOverview);
        
        // Initialize
        fetchModels();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


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
