import os
import json
from pathlib import Path
from typing import Dict, Any

# Default routing configuration
# Maps job_type -> {provider, model, endpoint}
DEFAULT_ROUTING_CONFIG = {
    "text-completion": {
        "provider": "openai",
        "model": "gpt-4",
        "endpoint": "/chat/completions"
    },
    "text-generation": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "endpoint": "/chat/completions"
    },
    "image-generation": {
        "provider": "stability",
        "model": "stable-diffusion-xl",
        "endpoint": "/images/generations"
    },
    "image-to-video": {
        "provider": "runway",
        "model": "gen-2",
        "endpoint": "/generations"
    },
    "video-generation": {
        "provider": "runway",
        "model": "gen-2",
        "endpoint": "/generations"
    },
    "audio-generation": {
        "provider": "elevenlabs",
        "model": "eleven_multilingual_v2",
        "endpoint": "/text-to-speech"
    },
    "text-to-speech": {
        "provider": "elevenlabs",
        "model": "eleven_multilingual_v2",
        "endpoint": "/text-to-speech"
    }
}

# Default pricing configuration
# Maps model -> cost structure
DEFAULT_PRICING_CONFIG = {
    "gpt-4": {
        "input_cost_per_1k": 0.03,
        "output_cost_per_1k": 0.06
    },
    "gpt-3.5-turbo": {
        "input_cost_per_1k": 0.001,
        "output_cost_per_1k": 0.002
    },
    "stable-diffusion-xl": {
        "per_image": 0.05
    },
    "gen-2": {
        "per_second": 0.10
    },
    "eleven_multilingual_v2": {
        "per_character": 0.0001
    }
}


def load_routing_config() -> Dict[str, Any]:
    """
    Load routing configuration from:
    1. ROUTING_CONFIG_JSON env var (inline JSON)
    2. ROUTING_CONFIG_PATH env var (file path)
    3. Default baked-in config
    """
    # Try inline JSON first
    config_json = os.getenv("ROUTING_CONFIG_JSON")
    if config_json:
        try:
            return json.loads(config_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid ROUTING_CONFIG_JSON: {e}")
    
    # Try file path
    config_path = os.getenv("ROUTING_CONFIG_PATH")
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise RuntimeError(f"ROUTING_CONFIG_PATH not found: {config_path}")
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in {config_path}: {e}")
    
    # Fallback to default
    return DEFAULT_ROUTING_CONFIG


def load_pricing_config() -> Dict[str, Any]:
    """
    Load pricing configuration from:
    1. PRICING_CONFIG_JSON env var (inline JSON)
    2. PRICING_CONFIG_PATH env var (file path)
    3. Default baked-in config
    """
    # Try inline JSON first
    config_json = os.getenv("PRICING_CONFIG_JSON")
    if config_json:
        try:
            return json.loads(config_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid PRICING_CONFIG_JSON: {e}")
    
    # Try file path
    config_path = os.getenv("PRICING_CONFIG_PATH")
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise RuntimeError(f"PRICING_CONFIG_PATH not found: {config_path}")
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in {config_path}: {e}")
    
    # Fallback to default
    return DEFAULT_PRICING_CONFIG


def get_admin_markup() -> tuple:
    """
    Get admin markup configuration from env vars.
    Returns (percent, fixed_fee) tuple.
    Defaults: 10% markup, $0.001 fixed fee
    """
    try:
        percent = float(os.getenv("ADMIN_MARKUP_PERCENT", "0.10"))
    except ValueError:
        percent = 0.10
    
    try:
        fixed_fee = float(os.getenv("ADMIN_FIXED_FEE", "0.001"))
    except ValueError:
        fixed_fee = 0.001
    
    return percent, fixed_fee


# Load configs at module init (fail fast if malformed)
ROUTING_CONFIG = load_routing_config()
PRICING_CONFIG = load_pricing_config()
ADMIN_MARKUP_PERCENT, ADMIN_FIXED_FEE = get_admin_markup()
