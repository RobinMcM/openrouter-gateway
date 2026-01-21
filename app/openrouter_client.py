import os
import httpx
from typing import Dict, Any, Tuple, Optional
from app.config import PRICING_CONFIG, ADMIN_MARKUP_PERCENT, ADMIN_FIXED_FEE

# Fail fast if OPENROUTER_API_KEY not set
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using chars/4 heuristic.
    This is a rough approximation - real tokenization varies by model.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def calculate_cost_estimate(
    routing: Dict[str, str],
    input_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate cost estimate based on job type and pricing config.
    
    Args:
        routing: {provider, model, endpoint}
        input_data: Optional data for estimation (prompt, image_count, duration, etc.)
    
    Returns:
        Cost breakdown with estimated=true flag
    """
    model = routing.get("model", "")
    pricing = PRICING_CONFIG.get(model, {})
    
    # Initialize estimate
    estimate = {
        "input_tokens": 0,
        "output_tokens": 0,
        "input_cost": 0.0,
        "output_cost": 0.0,
        "units": 0,
        "unit_cost": 0.0,
        "subtotal": 0.0,
        "admin_markup_percent": ADMIN_MARKUP_PERCENT,
        "admin_markup_fixed": ADMIN_FIXED_FEE,
        "admin_total": 0.0,
        "total": 0.0,
        "estimated": True,
        "warnings": []
    }
    
    input_data = input_data or {}
    
    # Text-based models (token pricing)
    if "input_cost_per_1k" in pricing:
        # Estimate input tokens from prompt
        prompt = input_data.get("prompt", "")
        messages = input_data.get("messages", [])
        
        # Extract text from messages if present
        if messages:
            prompt = " ".join([msg.get("content", "") for msg in messages if isinstance(msg, dict)])
        
        input_tokens = estimate_tokens(prompt)
        
        # Estimate output tokens (default to 150 if not specified)
        max_tokens = input_data.get("max_tokens", 150)
        output_tokens = max_tokens
        
        # Calculate costs
        input_cost = (input_tokens / 1000) * pricing.get("input_cost_per_1k", 0)
        output_cost = (output_tokens / 1000) * pricing.get("output_cost_per_1k", 0)
        
        estimate.update({
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "subtotal": round(input_cost + output_cost, 6)
        })
    
    # Image generation (per-image pricing)
    elif "per_image" in pricing:
        num_images = input_data.get("n", 1)
        unit_cost = pricing.get("per_image", 0)
        subtotal = num_images * unit_cost
        
        estimate.update({
            "units": num_images,
            "unit_type": "images",
            "unit_cost": unit_cost,
            "subtotal": round(subtotal, 6)
        })
    
    # Video generation (per-second pricing)
    elif "per_second" in pricing:
        duration = input_data.get("duration", 4)  # Default 4 seconds
        unit_cost = pricing.get("per_second", 0)
        subtotal = duration * unit_cost
        
        estimate.update({
            "units": duration,
            "unit_type": "seconds",
            "unit_cost": unit_cost,
            "subtotal": round(subtotal, 6)
        })
    
    # Audio/TTS (per-character pricing)
    elif "per_character" in pricing:
        text = input_data.get("text", "")
        num_chars = len(text)
        unit_cost = pricing.get("per_character", 0)
        subtotal = num_chars * unit_cost
        
        estimate.update({
            "units": num_chars,
            "unit_type": "characters",
            "unit_cost": unit_cost,
            "subtotal": round(subtotal, 6)
        })
    
    # Unknown pricing model
    else:
        estimate["warnings"].append(f"No pricing data for model '{model}'. Cost estimate may be inaccurate.")
        estimate["subtotal"] = 0.0
    
    # Calculate admin markup
    subtotal = estimate["subtotal"]
    admin_markup_amount = (subtotal * ADMIN_MARKUP_PERCENT) + ADMIN_FIXED_FEE
    total = subtotal + admin_markup_amount
    
    estimate.update({
        "admin_total": round(admin_markup_amount, 6),
        "total": round(total, 6)
    })
    
    return estimate


async def call_openrouter(
    endpoint: str,
    payload: Dict[str, Any]
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Call OpenRouter API.
    
    Args:
        endpoint: API endpoint path (e.g., "/chat/completions")
        payload: Request payload
    
    Returns:
        (success, response_data, error_message)
    
    Note: NEVER logs Authorization header or API key
    """
    url = f"{OPENROUTER_BASE_URL}{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                return True, response.json(), None
            else:
                error_msg = f"OpenRouter API error: {response.status_code} - {response.text[:500]}"
                return False, None, error_msg
    
    except httpx.TimeoutException:
        return False, None, "OpenRouter API request timed out"
    except httpx.RequestError as e:
        return False, None, f"OpenRouter API request failed: {str(e)}"
    except Exception as e:
        return False, None, f"Unexpected error calling OpenRouter: {str(e)}"


async def fetch_openrouter_models() -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch list of available models from OpenRouter API.
    
    Returns:
        (success, models_data, error_message)
    
    Note: NEVER logs Authorization header or API key
    """
    url = f"{OPENROUTER_BASE_URL}/models"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return True, response.json(), None
            else:
                error_msg = f"OpenRouter API error: {response.status_code} - {response.text[:500]}"
                return False, None, error_msg
    
    except httpx.TimeoutException:
        return False, None, "OpenRouter API request timed out"
    except httpx.RequestError as e:
        return False, None, f"OpenRouter API request failed: {str(e)}"
    except Exception as e:
        return False, None, f"Unexpected error fetching models: {str(e)}"


def filter_and_group_models(models_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out unavailable/experimental models and group into popular vs other.
    
    Top 10 popular models listed first, then remaining models alphabetically.
    
    Args:
        models_data: Raw response from OpenRouter /models endpoint
        
    Returns:
        Grouped models: {popular: [], other: [], total: int, filtered: int}
    """
    all_models = models_data.get("data", [])
    
    # Define top 10 most popular models (in order of popularity)
    popular_model_ids = [
        "openai/gpt-4-turbo",
        "openai/gpt-4",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet",
        "openai/gpt-3.5-turbo",
        "google/gemini-pro",
        "anthropic/claude-3-haiku",
        "meta-llama/llama-3-70b-instruct",
        "mistralai/mixtral-8x7b-instruct",
        "cohere/command-r-plus"
    ]
    
    # Filter models: exclude experimental, beta, and unavailable
    filtered_models = []
    for model in all_models:
        model_id = model.get("id", "")
        model_name = model.get("name", "")
        
        # Skip if model has beta/experimental indicators
        if any(x in model_id.lower() for x in ["beta", "experimental", "preview", "test"]):
            continue
        if any(x in model_name.lower() for x in ["beta", "experimental", "preview", "test"]):
            continue
            
        # Skip if explicitly marked as unavailable
        # (OpenRouter doesn't always have this field, so we check safely)
        if not model.get("context_length", 0) > 0:
            continue
            
        filtered_models.append(model)
    
    # Separate into popular and other
    popular = []
    other = []
    
    for model in filtered_models:
        model_id = model.get("id", "")
        if model_id in popular_model_ids:
            popular.append(model)
        else:
            other.append(model)
    
    # Sort popular by the predefined order
    popular_sorted = []
    for popular_id in popular_model_ids:
        for model in popular:
            if model.get("id") == popular_id:
                popular_sorted.append(model)
                break
    
    # Sort other alphabetically by name
    other_sorted = sorted(other, key=lambda m: m.get("name", "").lower())
    
    return {
        "popular": popular_sorted,
        "other": other_sorted,
        "total": len(all_models),
        "filtered": len(filtered_models)
    }


def extract_actual_usage(
    response: Dict[str, Any],
    routing: Dict[str, str]
) -> Dict[str, Any]:
    """
    Extract actual usage data from OpenRouter response.
    Falls back to estimate if usage data not available.
    
    Args:
        response: OpenRouter API response
        routing: Routing config
    
    Returns:
        Usage data with actual costs if available
    """
    model = routing.get("model", "")
    pricing = PRICING_CONFIG.get(model, {})
    
    # Try to extract usage from response
    usage = response.get("usage", {})
    
    if not usage:
        # No usage data - return estimate marker
        return {
            "estimated": True,
            "warning": "No usage data in response - costs are estimated"
        }
    
    # Calculate actual costs from usage
    result = {
        "estimated": False
    }
    
    # Token-based usage
    if "prompt_tokens" in usage or "completion_tokens" in usage:
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        input_cost = (prompt_tokens / 1000) * pricing.get("input_cost_per_1k", 0)
        output_cost = (completion_tokens / 1000) * pricing.get("output_cost_per_1k", 0)
        subtotal = input_cost + output_cost
        
        result.update({
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "subtotal": round(subtotal, 6)
        })
    else:
        # Other usage types - return what's available
        result.update(usage)
        result["estimated"] = True
        result["warning"] = "Usage format not recognized - costs may be estimated"
    
    # Add admin markup
    subtotal = result.get("subtotal", 0)
    admin_total = (subtotal * ADMIN_MARKUP_PERCENT) + ADMIN_FIXED_FEE
    total = subtotal + admin_total
    
    result.update({
        "admin_markup_percent": ADMIN_MARKUP_PERCENT,
        "admin_markup_fixed": ADMIN_FIXED_FEE,
        "admin_total": round(admin_total, 6),
        "total": round(total, 6)
    })
    
    return result
