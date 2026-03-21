from fastapi import FastAPI, Depends, Request, Query
from fastapi.responses import HTMLResponse
import uuid
from typing import Optional
from app.auth import verify_api_key, verify_admin_key
from app.schemas import (
    RouteRequest, RouteResponse, ExecuteRequest, ExecuteResponse,
    ErrorResponse, InstructionsResponse, EndpointInfo, LogsResponse,
    ModelsResponse, ModelInfo,
    UpdateOpenRouterKeyRequest, TestOpenRouterKeyRequest,
    TestOpenRouterKeyResponse, OpenRouterKeyStatusResponse,
    SuccessResponse, ModelsShowcaseResponse, ShowcaseCategory, ShowcaseModel,
    OpenRouterExecuteRequest, FalExecuteRequest, AsyncJobResponse, JobStatusResponse
)
from app.models_data import OPENROUTER_MODELS
from app.movieshaker_models_data import MOVIESHAKER_MODELS, CATEGORIES
from app.openrouter_models_showcase import OPENROUTER_SHOWCASE, OPENROUTER_CATEGORIES
from app.config_manager import (
    save_openrouter_key, is_key_configured, test_openrouter_key
)
from app.logger import get_sanitized_logs, log_request, log_success, log_error
from app.config import ROUTING_CONFIG
from app.providers.openrouter_client import (
    calculate_cost_estimate, call_openrouter, extract_actual_usage
)
# FAL gateway imports
from app.providers import fal_client
from app.routing.media_routing import get_routing_for_media_type, is_model_allowed, list_media_models
from app.pricing.media_pricing import calculate_cost_estimate as calculate_media_cost
from app.pricing.media_pricing import extract_actual_usage as extract_media_usage
from app.job_store.valkey_store import get_valkey_store

app = FastAPI(title="OpenRouter Gateway", version="1.0.0")

# CORS is now handled by Nginx to avoid duplicate headers
# FastAPI CORSMiddleware disabled - see nginx/conf.d/usageflows.conf for CORS configuration


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
    api_key: str = Depends(verify_admin_key)  # Correction #10: Admin-only
):
    """
    Get recent operational logs for debugging (ADMIN ONLY).
    Returns the last N lines from the log file (default 200, max 1000).
    All sensitive data is redacted before returning.
    
    Correction #10: Requires ADMIN_API_KEY if set, otherwise INTERNAL_API_KEY.
    """
    # Validate and cap lines parameter
    if lines > 1000:
        lines = 1000
    if lines < 1:
        lines = 1
    
    # Get sanitized logs
    logs = get_sanitized_logs(lines)
    
    return LogsResponse(lines=len(logs), logs=logs)


@app.get("/api/models")
async def get_models(api_key: str = Depends(verify_api_key)):
    """
    Get list of available OpenRouter models.
    Fetches real-time model list from OpenRouter API.
    Returns filtered models grouped into:
    - popular: Top 10 most popular models
    - other: All other models (alphabetically sorted)
    Excludes experimental, beta, and unavailable models.
    """
    from app.openrouter_client import fetch_openrouter_models, filter_and_group_models
    
    job_id = str(uuid.uuid4())
    log_request("models", job_id)
    
    try:
        success, models_data, error_msg = await fetch_openrouter_models()
        
        if not success:
            log_error(job_id, error_msg or "Failed to fetch models")
            return ErrorResponse(message=error_msg or "Failed to fetch models from OpenRouter")
        
        # Filter and group models
        grouped = filter_and_group_models(models_data)
        
        log_success(job_id, f"total={grouped['total']} filtered={grouped['filtered']} popular={len(grouped['popular'])}")
        
        # Return grouped models with backward compatibility
        all_models = grouped["popular"] + grouped["other"]
        
        return {
            "status": "ok",
            "models": all_models,  # Backward compatibility - all models in one list
            "popular": grouped["popular"],
            "other": grouped["other"],
            "total": grouped["total"],
            "filtered": grouped["filtered"],
            "count": len(all_models)  # Backward compatibility
        }
    
    except Exception as e:
        log_error(job_id, str(e))
        return ErrorResponse(message=f"Unexpected error: {str(e)}")


@app.get("/api/media/models")
async def get_media_models(
    media_type: Optional[str] = Query(default=None),
    api_key: str = Depends(verify_api_key),
):
    """
    List media-capable models for FAL usage.
    Optional media_type filter supports: image-generation, image-to-video,
    video-generation, audio-generation.
    """
    rows = list_media_models(media_type=media_type)
    return {
        "status": "ok",
        "models": rows,
        "count": len(rows),
        "media_type": media_type,
    }


@app.get("/api/models-showcase", response_model=ModelsShowcaseResponse)
async def get_models_showcase():
    """
    Get categorized AI models showcase for MovieShaker.
    Returns detailed information about models organized by use case.
    No authentication required - public information page.
    """
    categories = {}
    for category_id, category_data in MOVIESHAKER_MODELS.items():
        categories[category_id] = ShowcaseCategory(
            title=category_data["title"],
            icon=category_data["icon"],
            description=category_data["description"],
            models=[ShowcaseModel(**model) for model in category_data["models"]]
        )
    
    return ModelsShowcaseResponse(categories=categories)


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
    OpenRouter Models Showcase Page.
    Beautiful information display of OpenRouter models categorized by movieshaker.com use cases.
    No authentication required - public information page.
    """
    import json
    
    # Inject the OpenRouter showcase data into the HTML
    data_json = json.dumps(OPENROUTER_SHOWCASE)
    
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenRouter Models - MovieShaker</title>
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
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        
        .header h1 {
            font-size: 36px;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 18px;
            color: #666;
        }
        
        .nav-pills {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
            margin: 30px 0;
        }
        
        .nav-pill {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 50px;
            padding: 12px 24px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .nav-pill:hover {
            border-color: #667eea;
            background: #f0f7ff;
            transform: translateY(-2px);
        }
        
        .nav-pill.active {
            background: #667eea;
            border-color: #667eea;
            color: white;
        }
        
        .category-section {
            background: white;
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }
        
        .category-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
            padding-bottom: 20px;
            border-bottom: 3px solid #f0f0f0;
        }
        
        .category-icon {
            font-size: 48px;
        }
        
        .category-title h2 {
            font-size: 32px;
            color: #667eea;
        }
        
        .category-title p {
            font-size: 16px;
            color: #666;
            margin-top: 5px;
        }
        
        .models-grid {
            display: grid;
            gap: 30px;
            margin-top: 30px;
        }
        
        .model-card {
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 30px;
            transition: all 0.3s;
        }
        
        .model-card:hover {
            border-color: #667eea;
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
            transform: translateY(-4px);
        }
        
        .model-header {
            margin-bottom: 20px;
        }
        
        .model-name {
            font-size: 24px;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 5px;
        }
        
        .model-provider {
            font-size: 14px;
            color: #888;
        }
        
        .model-section {
            margin-bottom: 20px;
        }
        
        .model-section h4 {
            font-size: 14px;
            font-weight: 600;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .tag-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .tag {
            background: #f0f7ff;
            color: #667eea;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 14px;
            border: 1px solid #d0e7ff;
        }
        
        .tag.strength {
            background: #e8f5e9;
            color: #2e7d32;
            border-color: #c8e6c9;
        }
        
        .tag.limitation {
            background: #fff3e0;
            color: #e65100;
            border-color: #ffe0b2;
        }
        
        .text-list {
            list-style: none;
            padding-left: 0;
        }
        
        .text-list li {
            padding: 6px 0;
            padding-left: 20px;
            position: relative;
            line-height: 1.6;
            color: #555;
        }
        
        .text-list li:before {
            content: "•";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
        }
        
        .model-specs {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }
        
        .spec-item {
            display: flex;
            flex-direction: column;
        }
        
        .spec-label {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .spec-value {
            font-size: 16px;
            color: #333;
            font-weight: 600;
        }
        
        .footer {
            text-align: center;
            color: white;
            padding: 40px 20px;
            font-size: 14px;
        }
        
        .footer a {
            color: white;
            text-decoration: underline;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 28px;
            }
            
            .nav-pills {
                gap: 8px;
            }
            
            .nav-pill {
                padding: 10px 16px;
                font-size: 14px;
            }
            
            .category-section {
                padding: 20px;
            }
            
            .model-card {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 OpenRouter Models</h1>
            <p>AI models available through OpenRouter for film and music production</p>
        </div>
        
        <div class="nav-pills" id="categoryNav">
            <div class="nav-pill active" data-category="all">
                ✨ All Models
            </div>
        </div>
        
        <div id="categoriesContainer"></div>
        
        <div class="footer">
            <p>Powered by OpenRouter Gateway | <a href="/">Back to Home</a> | <a href="/models-showcase">View All AI Tools</a></p>
        </div>
    </div>
    
    <script>
        let showcaseData = {};
        
        // Inline data - OpenRouter models only
        const OPENROUTER_DATA = """ + data_json + """;
        
        // Load and display models
        function loadModels() {
            showcaseData = OPENROUTER_DATA;
            
            // Build category navigation
            const nav = document.getElementById('categoryNav');
            for (const [catId, catData] of Object.entries(showcaseData)) {
                const pill = document.createElement('div');
                pill.className = 'nav-pill';
                pill.dataset.category = catId;
                pill.innerHTML = `${catData.icon} ${catData.title}`;
                pill.addEventListener('click', () => filterCategory(catId));
                nav.appendChild(pill);
            }
            
            // Display all categories
            displayAllCategories();
        }
        
        function filterCategory(categoryId) {
            // Update active pill
            document.querySelectorAll('.nav-pill').forEach(pill => {
                pill.classList.remove('active');
            });
            event.target.classList.add('active');
            
            if (categoryId === 'all') {
                displayAllCategories();
            } else {
                displayCategory(categoryId);
            }
        }
        
        function displayAllCategories() {
            const container = document.getElementById('categoriesContainer');
            container.innerHTML = '';
            
            for (const [catId, catData] of Object.entries(showcaseData)) {
                container.appendChild(createCategorySection(catId, catData));
            }
        }
        
        function displayCategory(categoryId) {
            const container = document.getElementById('categoriesContainer');
            container.innerHTML = '';
            
            const catData = showcaseData[categoryId];
            if (catData) {
                container.appendChild(createCategorySection(categoryId, catData));
            }
        }
        
        function createCategorySection(categoryId, categoryData) {
            const section = document.createElement('div');
            section.className = 'category-section';
            section.id = `category-${categoryId}`;
            
            let html = `
                <div class="category-header">
                    <div class="category-icon">${categoryData.icon}</div>
                    <div class="category-title">
                        <h2>${categoryData.title}</h2>
                        <p>${categoryData.description}</p>
                    </div>
                </div>
                <div class="models-grid">
            `;
            
            categoryData.models.forEach(model => {
                html += createModelCard(model);
            });
            
            html += '</div>';
            section.innerHTML = html;
            
            return section;
        }
        
        function createModelCard(model) {
            return `
                <div class="model-card">
                    <div class="model-header">
                        <div class="model-name">${model.name}</div>
                        <div class="model-provider">by ${model.provider} • ${model.id}</div>
                    </div>
                    
                    <div class="model-section">
                        <h4>Best For</h4>
                        <div class="tag-list">
                            ${model.best_for.map(item => `<span class="tag">${item}</span>`).join('')}
                        </div>
                    </div>
                    
                    <div class="model-section">
                        <h4>Strengths</h4>
                        <div class="tag-list">
                            ${model.strengths.map(item => `<span class="tag strength">✓ ${item}</span>`).join('')}
                        </div>
                    </div>
                    
                    <div class="model-section">
                        <h4>Limitations</h4>
                        <div class="tag-list">
                            ${model.limitations.map(item => `<span class="tag limitation">! ${item}</span>`).join('')}
                        </div>
                    </div>
                    
                    <div class="model-section">
                        <h4>Use Cases</h4>
                        <ul class="text-list">
                            ${model.use_cases.map(useCase => `<li>${useCase}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="model-specs">
                        <div class="spec-item">
                            <div class="spec-label">Output</div>
                            <div class="spec-value">${model.output_specs}</div>
                        </div>
                        <div class="spec-item">
                            <div class="spec-label">Pricing</div>
                            <div class="spec-value">${model.estimated_cost}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Load models on page load
        loadModels();
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


@app.get("/models-showcase", response_class=HTMLResponse)
async def models_showcase_page():
    """
    MovieShaker AI Models Showcase Page.
    Beautiful information display of AI models categorized by use case.
    No authentication required - public information page.
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Models Showcase - MovieShaker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        
        .header h1 {
            font-size: 36px;
            color: #1e3c72;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 18px;
            color: #666;
        }
        
        .nav-pills {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
            margin: 30px 0;
        }
        
        .nav-pill {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 50px;
            padding: 12px 24px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .nav-pill:hover {
            border-color: #2a5298;
            background: #f0f7ff;
            transform: translateY(-2px);
        }
        
        .nav-pill.active {
            background: #2a5298;
            border-color: #2a5298;
            color: white;
        }
        
        .category-section {
            background: white;
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }
        
        .category-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
            padding-bottom: 20px;
            border-bottom: 3px solid #f0f0f0;
        }
        
        .category-icon {
            font-size: 48px;
        }
        
        .category-title h2 {
            font-size: 32px;
            color: #1e3c72;
        }
        
        .category-title p {
            font-size: 16px;
            color: #666;
            margin-top: 5px;
        }
        
        .models-grid {
            display: grid;
            gap: 30px;
            margin-top: 30px;
        }
        
        .model-card {
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 30px;
            transition: all 0.3s;
        }
        
        .model-card:hover {
            border-color: #2a5298;
            box-shadow: 0 8px 24px rgba(42, 82, 152, 0.15);
            transform: translateY(-4px);
        }
        
        .model-header {
            margin-bottom: 20px;
        }
        
        .model-name {
            font-size: 24px;
            font-weight: 600;
            color: #1e3c72;
            margin-bottom: 5px;
        }
        
        .model-provider {
            font-size: 14px;
            color: #888;
        }
        
        .model-section {
            margin-bottom: 20px;
        }
        
        .model-section h4 {
            font-size: 14px;
            font-weight: 600;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .tag-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .tag {
            background: #f0f7ff;
            color: #2a5298;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 14px;
            border: 1px solid #d0e7ff;
        }
        
        .tag.strength {
            background: #e8f5e9;
            color: #2e7d32;
            border-color: #c8e6c9;
        }
        
        .tag.limitation {
            background: #fff3e0;
            color: #e65100;
            border-color: #ffe0b2;
        }
        
        .text-list {
            list-style: none;
            padding-left: 0;
        }
        
        .text-list li {
            padding: 6px 0;
            padding-left: 20px;
            position: relative;
            line-height: 1.6;
            color: #555;
        }
        
        .text-list li:before {
            content: "•";
            position: absolute;
            left: 0;
            color: #2a5298;
            font-weight: bold;
        }
        
        .model-specs {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }
        
        .spec-item {
            display: flex;
            flex-direction: column;
        }
        
        .spec-label {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .spec-value {
            font-size: 16px;
            color: #333;
            font-weight: 600;
        }
        
        .footer {
            text-align: center;
            color: white;
            padding: 40px 20px;
            font-size: 14px;
        }
        
        .footer a {
            color: white;
            text-decoration: underline;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 28px;
            }
            
            .nav-pills {
                gap: 8px;
            }
            
            .nav-pill {
                padding: 10px 16px;
                font-size: 14px;
            }
            
            .category-section {
                padding: 20px;
            }
            
            .model-card {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 AI Models Showcase</h1>
            <p>Explore AI tools for film and music production</p>
        </div>
        
        <div class="nav-pills" id="categoryNav">
            <div class="nav-pill active" data-category="all">
                ✨ All Models
            </div>
        </div>
        
        <div id="categoriesContainer"></div>
        
        <div class="footer">
            <p>Powered by OpenRouter Gateway | <a href="/">Back to Home</a></p>
        </div>
    </div>
    
    <script>
        let showcaseData = {};
        
        // Fetch and display models
        async function loadModels() {
            try {
                const response = await fetch('/api/models-showcase');
                const data = await response.json();
                showcaseData = data.categories;
                
                // Build category navigation
                const nav = document.getElementById('categoryNav');
                for (const [catId, catData] of Object.entries(showcaseData)) {
                    const pill = document.createElement('div');
                    pill.className = 'nav-pill';
                    pill.dataset.category = catId;
                    pill.innerHTML = `${catData.icon} ${catData.title}`;
                    pill.addEventListener('click', () => filterCategory(catId));
                    nav.appendChild(pill);
                }
                
                // Display all categories
                displayAllCategories();
                
            } catch (error) {
                console.error('Error loading models:', error);
                document.getElementById('categoriesContainer').innerHTML = 
                    '<div class="category-section"><p>Error loading models. Please try again later.</p></div>';
            }
        }
        
        function filterCategory(categoryId) {
            // Update active pill
            document.querySelectorAll('.nav-pill').forEach(pill => {
                pill.classList.remove('active');
            });
            event.target.classList.add('active');
            
            if (categoryId === 'all') {
                displayAllCategories();
            } else {
                displayCategory(categoryId);
            }
        }
        
        function displayAllCategories() {
            const container = document.getElementById('categoriesContainer');
            container.innerHTML = '';
            
            for (const [catId, catData] of Object.entries(showcaseData)) {
                container.appendChild(createCategorySection(catId, catData));
            }
        }
        
        function displayCategory(categoryId) {
            const container = document.getElementById('categoriesContainer');
            container.innerHTML = '';
            
            const catData = showcaseData[categoryId];
            if (catData) {
                container.appendChild(createCategorySection(categoryId, catData));
            }
        }
        
        function createCategorySection(categoryId, categoryData) {
            const section = document.createElement('div');
            section.className = 'category-section';
            section.id = `category-${categoryId}`;
            
            let html = `
                <div class="category-header">
                    <div class="category-icon">${categoryData.icon}</div>
                    <div class="category-title">
                        <h2>${categoryData.title}</h2>
                        <p>${categoryData.description}</p>
                    </div>
                </div>
                <div class="models-grid">
            `;
            
            categoryData.models.forEach(model => {
                html += createModelCard(model);
            });
            
            html += '</div>';
            section.innerHTML = html;
            
            return section;
        }
        
        function createModelCard(model) {
            return `
                <div class="model-card">
                    <div class="model-header">
                        <div class="model-name">${model.name}</div>
                        <div class="model-provider">by ${model.provider}</div>
                    </div>
                    
                    <div class="model-section">
                        <h4>Best For</h4>
                        <div class="tag-list">
                            ${model.best_for.map(item => `<span class="tag">${item}</span>`).join('')}
                        </div>
                    </div>
                    
                    <div class="model-section">
                        <h4>Strengths</h4>
                        <div class="tag-list">
                            ${model.strengths.map(item => `<span class="tag strength">✓ ${item}</span>`).join('')}
                        </div>
                    </div>
                    
                    <div class="model-section">
                        <h4>Limitations</h4>
                        <div class="tag-list">
                            ${model.limitations.map(item => `<span class="tag limitation">! ${item}</span>`).join('')}
                        </div>
                    </div>
                    
                    <div class="model-section">
                        <h4>Use Cases</h4>
                        <ul class="text-list">
                            ${model.use_cases.map(useCase => `<li>${useCase}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="model-specs">
                        <div class="spec-item">
                            <div class="spec-label">Output</div>
                            <div class="spec-value">${model.output_specs}</div>
                        </div>
                        <div class="spec-item">
                            <div class="spec-label">Estimated Cost</div>
                            <div class="spec-value">${model.estimated_cost}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Load models on page load
        loadModels();
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


@app.post("/api/execute")
async def execute_request(
    request: Request,  # Use FastAPI Request object
    api_key: str = Depends(verify_api_key)
):
    """
    Execute API call with provider routing (OpenRouter or FAL).
    
    Supports both:
    - New format: discriminated union on 'provider' field
    - Old format: no provider field (defaults to OpenRouter)
    """
    # Get the raw JSON body
    body = await request.json()
    
    # Check if provider field exists, default to openrouter for backward compatibility
    if "provider" not in body:
        body["provider"] = "openrouter"
    
    provider = body["provider"]
    
    if provider == "openrouter":
        # Parse as OpenRouterExecuteRequest
        openrouter_request = OpenRouterExecuteRequest(**body)
        return await execute_openrouter(openrouter_request)
    elif provider == "fal":
        # Parse as FalExecuteRequest
        fal_request = FalExecuteRequest(**body)
        return await execute_fal(fal_request)
    else:
        return ErrorResponse(message=f"Unknown provider: {provider}")


async def execute_openrouter(request: OpenRouterExecuteRequest) -> ExecuteResponse | ErrorResponse:
    """
    Handle OpenRouter execution (existing logic).
    """
    job_id = str(uuid.uuid4())
    log_request("execute_openrouter", job_id)
    
    try:
        job_type = request.job_type
        
        if job_type not in ROUTING_CONFIG:
            log_error(job_id, f"Unknown job_type: {job_type}")
            return ErrorResponse(message=f"Unknown job_type: {job_type}")
        
        routing = ROUTING_CONFIG[job_type]
        
        # Override routing with actual model from payload
        if "model" in request.payload:
            routing = routing.copy()
            routing["model"] = request.payload["model"]
            if "/" in routing["model"]:
                routing["provider"] = routing["model"].split("/")[0]
        
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
        
        usage = extract_actual_usage(response_data, routing)
        log_success(job_id, f"job_type={job_type} model={routing.get('model')}")
        
        return ExecuteResponse(
            routing=routing,
            result=response_data,
            usage=usage
        )
    
    except Exception as e:
        log_error(job_id, str(e))
        return ErrorResponse(message=f"Unexpected error: {str(e)}")


async def execute_fal(request: FalExecuteRequest) -> AsyncJobResponse | ErrorResponse:
    """
    Handle FAL execution (async with job queue).
    Returns job_id immediately, client polls /api/status/{job_id}.
    """
    job_id = str(uuid.uuid4())
    log_request("execute_fal", job_id)
    
    try:
        # Get routing for media_type with optional model override (Correction #9)
        routing_config = get_routing_for_media_type(request.media_type, request.model)
        
        if not routing_config:
            if request.model and not is_model_allowed(request.model):
                log_error(job_id, f"Model not allowed: {request.model}")
                return ErrorResponse(message=f"Model '{request.model}' not in allowlist")
            log_error(job_id, f"Unknown media_type: {request.media_type}")
            return ErrorResponse(message=f"Unknown media_type: {request.media_type}")
        
        model = routing_config["model"]
        mode = routing_config.get("mode", "queue")
        
        # Calculate cost estimate
        estimate = calculate_media_cost(model, request.payload)
        
        # Dry run - return estimate only
        if request.dry_run:
            log_success(job_id, f"dry_run=true media_type={request.media_type} model={model}")
            return AsyncJobResponse(
                ok=True,
                job_id=job_id,
                job_status="completed",
                status_url=f"/api/status/{job_id}",
                estimate=estimate
            )
        
        # Create job in Valkey
        valkey = await get_valkey_store()
        await valkey.create_job(
            job_id=job_id,
            provider="fal",
            media_type=request.media_type,
            model=model,
            payload=request.payload,
            estimate=estimate
        )
        
        # Submit to FAL (queue mode)
        success, provider_request_id, error_msg = await fal_client.submit_queue(
            model_id=model,
            payload=request.payload,
            webhook_url=request.webhook_url
        )
        
        if not success:
            await valkey.update_job(job_id, status="failed", error=error_msg)
            log_error(job_id, error_msg or "FAL submission failed")
            return ErrorResponse(message=error_msg or "FAL submission failed")
        
        # Update job with provider request ID
        await valkey.update_job(
            job_id,
            status="processing",
            provider_request_id=provider_request_id
        )
        
        log_success(job_id, f"media_type={request.media_type} model={model} provider_request_id={provider_request_id}")
        
        return AsyncJobResponse(
            ok=True,
            job_id=job_id,
            job_status="processing",
            status_url=f"/api/status/{job_id}",
            estimate=estimate
        )
    
    except Exception as e:
        log_error(job_id, str(e))
        return ErrorResponse(message=f"Unexpected error: {str(e)}")


@app.get("/api/status/{job_id}", response_model=JobStatusResponse | ErrorResponse)
async def get_job_status(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get status of FAL job.
    
    Correction #4: Transient errors don't fail the job, only terminal states do.
    
    Returns:
    - queued: Job submitted but not started
    - processing: Job in progress
    - completed: Job done, result available
    - failed: Job failed (terminal error only)
    """
    log_request("status", job_id)
    
    try:
        valkey = await get_valkey_store()
        job = await valkey.get_job(job_id)
        
        if not job:
            log_error(job_id, "Job not found")
            return ErrorResponse(message=f"Job {job_id} not found")
        
        current_status = job.get("status")
        
        # If already completed or failed, return cached result
        if current_status in ["completed", "failed"]:
            log_success(job_id, f"status={current_status} (cached)")
            
            return JobStatusResponse(
                ok=(current_status == "completed"),
                job_id=job_id,
                job_status=current_status,
                result=job.get("result"),
                usage=job.get("estimate"),  # Or actual usage if available
                error=job.get("error")
            )
        
        # Job still processing - check FAL status
        # Correction #3: Acquire lock to prevent concurrent status checks
        lock_acquired = await valkey.acquire_lock(job_id, timeout_seconds=10)
        
        if not lock_acquired:
            # Another request is checking status, return current state
            log_success(job_id, f"status={current_status} (locked)")
            return JobStatusResponse(
                ok=True,
                job_id=job_id,
                job_status=current_status,
                provider_status=None,
                warning="Status check in progress by another request"
            )
        
        # Check FAL status
        provider_request_id = job.get("provider_request_id")
        model = job.get("model")
        
        if not provider_request_id or not model:
            log_error(job_id, "Missing provider_request_id or model")
            return ErrorResponse(message="Invalid job state")
        
        # Correction #4: Transient errors should not fail the job
        success, status_data, error_msg = await fal_client.get_queue_status(
            model, provider_request_id, job_id=job_id
        )
        
        if not success:
            # Transient error - keep job as processing, return warning
            log_error(job_id, f"Transient status error: {error_msg}")
            return JobStatusResponse(
                ok=True,
                job_id=job_id,
                job_status="processing",
                provider_status=None,
                warning=f"Transient error checking status: {error_msg}"
            )
        
        fal_status = status_data.get("status", "UNKNOWN")
        
        # Job still queued or in progress
        if fal_status in ["IN_QUEUE", "IN_PROGRESS"]:
            log_success(job_id, f"fal_status={fal_status}")
            return JobStatusResponse(
                ok=True,
                job_id=job_id,
                job_status="processing",
                provider_status=status_data
            )
        
        # Job completed - fetch result
        if fal_status == "COMPLETED":
            response_url = status_data.get("response_url")
            
            if not response_url:
                log_error(job_id, "No response_url in completed status")
                await valkey.update_job(job_id, status="failed", error="No response_url from FAL")
                return ErrorResponse(message="FAL returned COMPLETED but no response_url")
            
            # Fetch result (Correction #5: validates host and includes auth)
            success, result_data, error_msg = await fal_client.fetch_queue_result(response_url)
            
            if not success:
                log_error(job_id, f"Failed to fetch result: {error_msg}")
                await valkey.update_job(job_id, status="failed", error=error_msg)
                return ErrorResponse(message=f"Failed to fetch result: {error_msg}")
            
            # Parse result (Correction #8: handles multiple formats)
            parsed_result = fal_client.parse_fal_result(result_data)
            
            # Calculate actual usage
            payload = job.get("payload", {})
            usage = extract_media_usage(result_data, model, payload)
            
            # Store result in Valkey
            await valkey.update_job(
                job_id,
                status="completed",
                result_json=parsed_result,
                estimate_json=usage
            )
            
            log_success(job_id, f"status=completed files={len(parsed_result.get('files', []))}")
            
            return JobStatusResponse(
                ok=True,
                job_id=job_id,
                job_status="completed",
                result=parsed_result,
                usage=usage
            )
        
        # Job failed (terminal failure from FAL)
        else:
            error_detail = status_data.get("error", f"FAL status: {fal_status}")
            await valkey.update_job(job_id, status="failed", error=error_detail)
            log_error(job_id, f"FAL job failed: {error_detail}")
            
            return JobStatusResponse(
                ok=False,
                job_id=job_id,
                job_status="failed",
                error=error_detail
            )
    
    except Exception as e:
        log_error(job_id, f"Unexpected error: {str(e)}")
        return ErrorResponse(message=f"Unexpected error: {str(e)}")


@app.get("/api/result/{job_id}")
async def get_job_result(
    job_id: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Return result payload for a previously submitted async job.
    Keeps compatibility with clients that probe /api/result/{job_id}.
    """
    valkey = await get_valkey_store()
    job = await valkey.get_job(job_id)
    if not job:
        return ErrorResponse(message=f"Job {job_id} not found")
    return {
        "status": "ok",
        "ok": job.get("status") == "completed",
        "job_id": job_id,
        "job_status": job.get("status"),
        "result": job.get("result"),
        "usage": job.get("estimate"),
        "error": job.get("error"),
    }


@app.get("/api/results/{job_id}")
async def get_job_results_alias(
    job_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Alias for /api/result/{job_id}."""
    return await get_job_result(job_id=job_id, api_key=api_key)
