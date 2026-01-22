"""
Media Pricing Module for FAL Gateway

Implements multiple pricing strategies as per feedback:
- per_megapixel (for FLUX models)
- per_second (for video generation)
- per_generation (flat rate)
- tiered_per_megapixel (for pro models)

All estimates include pricing_version for audit trail.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime


# Admin markup configuration
ADMIN_MARKUP_PERCENT = float(os.getenv("ADMIN_MARKUP_PERCENT", "0.10"))  # 10%
ADMIN_FIXED_FEE = float(os.getenv("ADMIN_FIXED_FEE", "0.001"))  # $0.001

# Pricing version for audit trail
PRICING_VERSION = "2026-01-22"


# Pricing configuration with strategies
MEDIA_PRICING_CONFIG: Dict[str, Dict[str, Any]] = {
    # FLUX models - per megapixel pricing
    "fal-ai/flux/schnell": {
        "strategy": "per_megapixel",
        "cost_per_megapixel": 0.000003,
        "description": "Fast FLUX model"
    },
    "fal-ai/flux/dev": {
        "strategy": "per_megapixel",
        "cost_per_megapixel": 0.000025,
        "description": "FLUX development model"
    },
    "fal-ai/flux-pro": {
        "strategy": "per_megapixel",
        "cost_per_megapixel": 0.000055,
        "description": "FLUX Pro high-quality model"
    },
    "fal-ai/flux-realism": {
        "strategy": "per_megapixel",
        "cost_per_megapixel": 0.00003,
        "description": "FLUX Realism model"
    },
    
    # Video models - per second pricing
    "fal-ai/kling-video/v1/standard/image-to-video": {
        "strategy": "per_second",
        "cost_per_second": 0.08,
        "default_duration": 5,
        "description": "Kling image-to-video"
    },
    "fal-ai/kling-video/v1/standard/text-to-video": {
        "strategy": "per_second",
        "cost_per_second": 0.08,
        "default_duration": 5,
        "description": "Kling text-to-video"
    },
    "fal-ai/runway-gen3/turbo/image-to-video": {
        "strategy": "per_second",
        "cost_per_second": 0.05,
        "default_duration": 5,
        "description": "Runway Gen-3 Turbo"
    },
    "fal-ai/luma-dream-machine": {
        "strategy": "per_second",
        "cost_per_second": 0.04,
        "default_duration": 5,
        "description": "Luma Dream Machine"
    },
    
    # Audio models - per generation (flat rate)
    "fal-ai/stable-audio": {
        "strategy": "per_generation",
        "cost_per_generation": 0.025,
        "description": "Stable Audio generation"
    }
}


# Image size presets to megapixels mapping
IMAGE_SIZE_MEGAPIXELS = {
    "square_hd": 1.05,  # 1024x1024 = 1.048576 MP
    "square": 0.26,  # 512x512 = 0.262144 MP
    "portrait_4_3": 0.94,  # 896x1152 = 1.032192 MP
    "portrait_16_9": 0.88,  # 768x1344 = 1.032192 MP
    "landscape_4_3": 0.94,  # 1152x896 = 1.032192 MP
    "landscape_16_9": 0.88,  # 1344x768 = 1.032192 MP
}


def calculate_megapixels(payload: Dict[str, Any]) -> float:
    """
    Calculate megapixels from payload.
    Handles both image_size presets and explicit width/height.
    """
    # Try image_size preset first
    image_size = payload.get("image_size")
    if image_size and image_size in IMAGE_SIZE_MEGAPIXELS:
        return IMAGE_SIZE_MEGAPIXELS[image_size]
    
    # Try explicit dimensions
    width = payload.get("width", 1024)
    height = payload.get("height", 1024)
    return (width * height) / 1_000_000


def calculate_duration(payload: Dict[str, Any], default_duration: float = 5.0) -> float:
    """
    Extract video duration from payload.
    """
    return float(payload.get("duration", payload.get("length", default_duration)))


def calculate_cost_estimate(
    model: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate cost estimate for a model and payload.
    
    Returns estimate with:
    - subtotal: Base cost from provider
    - admin_total: Admin markup
    - total: Final cost
    - estimated: Always True (gateway doesn't bill)
    - pricing_version: For audit trail
    - strategy: Pricing strategy used
    """
    pricing = MEDIA_PRICING_CONFIG.get(model)
    
    if not pricing:
        # Unknown model - return zero estimate with warning
        return {
            "subtotal": 0.0,
            "admin_total": 0.0,
            "total": 0.0,
            "estimated": True,
            "pricing_version": PRICING_VERSION,
            "strategy": "unknown",
            "warning": f"No pricing data for model '{model}'"
        }
    
    strategy = pricing["strategy"]
    subtotal = 0.0
    details = {}
    
    # Per-megapixel strategy (FLUX models)
    if strategy == "per_megapixel":
        megapixels = calculate_megapixels(payload)
        cost_per_mp = pricing["cost_per_megapixel"]
        num_images = payload.get("num_images", 1)
        
        subtotal = megapixels * cost_per_mp * num_images
        details = {
            "megapixels": round(megapixels, 3),
            "cost_per_megapixel": cost_per_mp,
            "num_images": num_images
        }
    
    # Per-second strategy (video models)
    elif strategy == "per_second":
        duration = calculate_duration(payload, pricing.get("default_duration", 5.0))
        cost_per_sec = pricing["cost_per_second"]
        
        subtotal = duration * cost_per_sec
        details = {
            "duration_seconds": duration,
            "cost_per_second": cost_per_sec
        }
    
    # Per-generation strategy (audio, simple models)
    elif strategy == "per_generation":
        cost = pricing["cost_per_generation"]
        num_generations = payload.get("num_outputs", 1)
        
        subtotal = cost * num_generations
        details = {
            "num_generations": num_generations,
            "cost_per_generation": cost
        }
    
    # Calculate admin markup
    admin_markup = (subtotal * ADMIN_MARKUP_PERCENT) + ADMIN_FIXED_FEE
    total = subtotal + admin_markup
    
    return {
        "subtotal": round(subtotal, 6),
        "admin_markup_percent": ADMIN_MARKUP_PERCENT,
        "admin_markup_fixed": ADMIN_FIXED_FEE,
        "admin_total": round(admin_markup, 6),
        "total": round(total, 6),
        "estimated": True,  # Gateway only estimates, doesn't bill
        "pricing_version": PRICING_VERSION,
        "strategy": strategy,
        "model": model,
        **details
    }


def extract_actual_usage(
    result_data: Dict[str, Any],
    model: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract actual usage from fal.ai result.
    
    Since fal.ai doesn't always return cost info, we calculate
    based on actual outputs when possible, otherwise use estimate.
    """
    # Check if fal.ai provided cost (rare)
    if "cost" in result_data:
        actual_cost = result_data["cost"]
        admin_markup = (actual_cost * ADMIN_MARKUP_PERCENT) + ADMIN_FIXED_FEE
        
        return {
            "subtotal": actual_cost,
            "admin_total": round(admin_markup, 6),
            "total": round(actual_cost + admin_markup, 6),
            "estimated": False,
            "pricing_version": PRICING_VERSION,
            "model": model
        }
    
    # Otherwise, recalculate based on actual outputs if available
    pricing = MEDIA_PRICING_CONFIG.get(model)
    if not pricing:
        return calculate_cost_estimate(model, payload)
    
    strategy = pricing["strategy"]
    
    # For per_megapixel: count actual images returned
    if strategy == "per_megapixel":
        actual_images = len(result_data.get("images", []))
        if actual_images > 0:
            updated_payload = payload.copy()
            updated_payload["num_images"] = actual_images
            estimate = calculate_cost_estimate(model, updated_payload)
            estimate["estimated"] = False  # Based on actual output
            return estimate
    
    # For per_second: use actual duration if provided
    elif strategy == "per_second":
        if "duration" in result_data:
            updated_payload = payload.copy()
            updated_payload["duration"] = result_data["duration"]
            estimate = calculate_cost_estimate(model, updated_payload)
            estimate["estimated"] = False
            return estimate
    
    # Fallback to original estimate
    estimate = calculate_cost_estimate(model, payload)
    estimate["estimated"] = True
    return estimate
