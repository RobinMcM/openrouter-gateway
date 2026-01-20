from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
import uuid
from app.auth import verify_api_key
from app.schemas import (
    RouteRequest, RouteResponse, ExecuteRequest, ExecuteResponse,
    ErrorResponse, InstructionsResponse, EndpointInfo, LogsResponse,
    ModelsResponse, ModelInfo,
    UpdateOpenRouterKeyRequest, TestOpenRouterKeyRequest,
    TestOpenRouterKeyResponse, OpenRouterKeyStatusResponse,
    SuccessResponse
)
from app.models_data import OPENROUTER_MODELS
from app.config_manager import (
    save_openrouter_key, is_key_configured, test_openrouter_key
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


@app.get("/api/models", response_model=ModelsResponse)
async def get_models(api_key: str = Depends(verify_api_key)):
    """
    Get list of available OpenRouter models.
    Returns a static list of popular models with basic information.
    No external API calls - data is hardcoded from OpenRouter's public website.
    """
    models = [ModelInfo(**model) for model in OPENROUTER_MODELS]
    return ModelsResponse(models=models)


@app.get("/api/config/openrouter-key/status", response_model=OpenRouterKeyStatusResponse)
async def get_openrouter_key_status(api_key: str = Depends(verify_api_key)):
    """
    Check if OpenRouter API key is configured.
    Does NOT return the actual key value - only returns whether it's configured.
    """
    configured = is_key_configured()
    message = "OpenRouter API key is configured" if configured else "OpenRouter API key is not configured"
    return OpenRouterKeyStatusResponse(configured=configured, message=message)


@app.post("/api/config/test-openrouter-key", response_model=TestOpenRouterKeyResponse)
async def test_key(request: TestOpenRouterKeyRequest, api_key: str = Depends(verify_api_key)):
    """
    Test an OpenRouter API key without saving it.
    Makes a test API call to OpenRouter to verify the key is valid.
    The key is NOT saved or stored in any way.
    """
    valid, message = await test_openrouter_key(request.api_key)
    status = "ok" if valid else "error"
    return TestOpenRouterKeyResponse(status=status, valid=valid, message=message)


@app.post("/api/config/openrouter-key", response_model=SuccessResponse | ErrorResponse)
async def update_openrouter_key(request: UpdateOpenRouterKeyRequest, api_key: str = Depends(verify_api_key)):
    """
    Update the OpenRouter API key configuration.
    The key is saved to a secure config file and can ONLY be updated, never read or displayed.
    This ensures the key remains write-only and is never exposed via the API.
    """
    success, message = save_openrouter_key(request.api_key)
    
    if success:
        return SuccessResponse(message=message)
    else:
        return ErrorResponse(message=message)


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


@app.get("/config", response_class=HTMLResponse)
async def config_page():
    """
    Owner configuration page for managing OpenRouter API key.
    Allows testing and updating the API key (write-only, never displayed).
    Does not require authentication - meant for owner access only.
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Owner Configuration - OpenRouter Gateway</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 700px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
        
        .status-section {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            border-left: 4px solid #f5576c;
        }
        
        .status-section h2 {
            color: #f5576c;
            font-size: 18px;
            margin-bottom: 10px;
        }
        
        .status-text {
            color: #666;
            font-size: 14px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 10px;
        }
        
        .status-badge.configured {
            background: #d4edda;
            color: #155724;
        }
        
        .status-badge.not-configured {
            background: #f8d7da;
            color: #721c24;
        }
        
        .form-section {
            margin-bottom: 30px;
        }
        
        .form-section h2 {
            color: #333;
            font-size: 20px;
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }
        
        input[type="password"],
        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.3s;
            font-family: monospace;
        }
        
        input:focus {
            border-color: #f5576c;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        button {
            flex: 1;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(245, 87, 108, 0.4);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
            transform: translateY(-2px);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        
        .alert.active {
            display: block;
            animation: fadeIn 0.3s;
        }
        
        .alert-success {
            background: #d4edda;
            border-left: 4px solid #28a745;
            color: #155724;
        }
        
        .alert-error {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            color: #721c24;
        }
        
        .alert-info {
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            color: #0c5460;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .help-text {
            font-size: 13px;
            color: #666;
            margin-top: 8px;
            font-style: italic;
        }
        
        .warning-box {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
            color: #856404;
        }
        
        .warning-box strong {
            display: block;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ Owner Configuration</h1>
            <p>Manage your OpenRouter API key</p>
        </div>
        
        <div class="content">
            <div id="alertMessage" class="alert"></div>
            
            <div class="status-section">
                <h2>Current Status</h2>
                <p class="status-text" id="statusText">Checking configuration...</p>
                <span class="status-badge" id="statusBadge">Loading...</span>
            </div>
            
            <div class="form-section">
                <h2>Update OpenRouter API Key</h2>
                
                <label for="apiKey">OpenRouter API Key</label>
                <input 
                    type="password" 
                    id="apiKey" 
                    placeholder="sk-or-v1-..." 
                    autocomplete="off"
                />
                <p class="help-text">Your API key from openrouter.ai (starts with sk-or-v1-)</p>
                
                <div class="button-group">
                    <button type="button" class="btn-secondary" id="testButton">
                        Test Key
                    </button>
                    <button type="button" class="btn-primary" id="saveButton">
                        Save Key
                    </button>
                </div>
                
                <div class="warning-box">
                    <strong>🔒 Security Notice:</strong>
                    Once saved, your API key cannot be viewed or retrieved through this interface. 
                    It can only be updated. Keep a backup of your key in a secure location.
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const apiKeyInput = document.getElementById('apiKey');
        const testButton = document.getElementById('testButton');
        const saveButton = document.getElementById('saveButton');
        const alertMessage = document.getElementById('alertMessage');
        const statusText = document.getElementById('statusText');
        const statusBadge = document.getElementById('statusBadge');
        
        let internalApiKey = '';
        
        // Check current configuration status
        async function checkStatus() {
            try {
                if (!internalApiKey) {
                    internalApiKey = prompt('Please enter your Internal API Key (X-Internal-API-Key):');
                    if (!internalApiKey) {
                        showAlert('Internal API key is required', 'error');
                        return;
                    }
                }
                
                const response = await fetch('/api/config/openrouter-key/status', {
                    headers: {
                        'X-Internal-API-Key': internalApiKey
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.configured) {
                    statusText.textContent = 'OpenRouter API key is configured and ready to use.';
                    statusBadge.textContent = '✓ Configured';
                    statusBadge.className = 'status-badge configured';
                } else {
                    statusText.textContent = 'No OpenRouter API key is currently configured. Please add one below.';
                    statusBadge.textContent = '✗ Not Configured';
                    statusBadge.className = 'status-badge not-configured';
                }
                
            } catch (error) {
                statusText.textContent = 'Failed to check configuration status.';
                statusBadge.textContent = 'Error';
                statusBadge.className = 'status-badge not-configured';
                showAlert('Error: ' + error.message, 'error');
            }
        }
        
        // Test API key
        async function testApiKey() {
            const key = apiKeyInput.value.trim();
            
            if (!key) {
                showAlert('Please enter an API key to test', 'error');
                return;
            }
            
            testButton.disabled = true;
            testButton.textContent = 'Testing...';
            
            try {
                const response = await fetch('/api/config/test-openrouter-key', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Internal-API-Key': internalApiKey
                    },
                    body: JSON.stringify({ api_key: key })
                });
                
                const data = await response.json();
                
                if (data.valid) {
                    showAlert('✓ ' + data.message, 'success');
                } else {
                    showAlert('✗ ' + data.message, 'error');
                }
                
            } catch (error) {
                showAlert('Test failed: ' + error.message, 'error');
            } finally {
                testButton.disabled = false;
                testButton.textContent = 'Test Key';
            }
        }
        
        // Save API key
        async function saveApiKey() {
            const key = apiKeyInput.value.trim();
            
            if (!key) {
                showAlert('Please enter an API key to save', 'error');
                return;
            }
            
            if (!confirm('Are you sure you want to save this API key? Once saved, it cannot be viewed through this interface.')) {
                return;
            }
            
            saveButton.disabled = true;
            saveButton.textContent = 'Saving...';
            
            try {
                const response = await fetch('/api/config/openrouter-key', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Internal-API-Key': internalApiKey
                    },
                    body: JSON.stringify({ api_key: key })
                });
                
                const data = await response.json();
                
                if (data.status === 'ok') {
                    showAlert('✓ ' + data.message, 'success');
                    apiKeyInput.value = '';
                    checkStatus();
                } else {
                    showAlert('✗ ' + data.message, 'error');
                }
                
            } catch (error) {
                showAlert('Save failed: ' + error.message, 'error');
            } finally {
                saveButton.disabled = false;
                saveButton.textContent = 'Save Key';
            }
        }
        
        // Show alert message
        function showAlert(message, type) {
            alertMessage.textContent = message;
            alertMessage.className = `alert alert-${type} active`;
            
            setTimeout(() => {
                alertMessage.classList.remove('active');
            }, 5000);
        }
        
        // Event listeners
        testButton.addEventListener('click', testApiKey);
        saveButton.addEventListener('click', saveApiKey);
        
        // Initialize
        checkStatus();
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
