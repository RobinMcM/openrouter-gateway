"""
Configuration Manager
Handles OpenRouter API key storage and validation.
Keys are write-only - can be updated but never read/displayed.
"""

import os
from pathlib import Path
from typing import Tuple
import httpx


# Configuration file path
CONFIG_DIR = Path("/app/config")
OPENROUTER_KEY_FILE = CONFIG_DIR / "openrouter.key"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def ensure_config_dir():
    """Ensure configuration directory exists with proper permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Set restrictive permissions (owner read/write only)
    CONFIG_DIR.chmod(0o700)


def save_openrouter_key(api_key: str) -> Tuple[bool, str]:
    """
    Save OpenRouter API key to secure config file.
    
    Args:
        api_key: OpenRouter API key to save
    
    Returns:
        (success, message) tuple
    """
    try:
        ensure_config_dir()
        
        # Validate key format (basic check)
        if not api_key.startswith("sk-or-v1-"):
            return False, "Invalid API key format. Must start with 'sk-or-v1-'"
        
        # Write key to file with restrictive permissions
        OPENROUTER_KEY_FILE.write_text(api_key)
        OPENROUTER_KEY_FILE.chmod(0o600)  # Owner read/write only
        
        return True, "OpenRouter API key saved successfully"
    
    except PermissionError:
        return False, "Permission denied: Cannot write to config directory"
    except Exception as e:
        return False, f"Failed to save API key: {str(e)}"


def is_key_configured() -> bool:
    """
    Check if OpenRouter API key is configured.
    Does NOT read or expose the actual key value.
    
    Returns:
        True if key file exists and is not empty
    """
    try:
        return OPENROUTER_KEY_FILE.exists() and OPENROUTER_KEY_FILE.stat().st_size > 0
    except Exception:
        return False


def get_configured_key() -> str:
    """
    Internal function to read the configured key for API calls.
    This should ONLY be used internally, never exposed via API.
    
    Returns:
        API key string, or empty string if not configured
    """
    try:
        if OPENROUTER_KEY_FILE.exists():
            return OPENROUTER_KEY_FILE.read_text().strip()
        return ""
    except Exception:
        return ""


async def test_openrouter_key(api_key: str) -> Tuple[bool, str]:
    """
    Test if an OpenRouter API key is valid by making a test API call.
    
    Args:
        api_key: OpenRouter API key to test
    
    Returns:
        (valid, message) tuple
    """
    # Basic format validation
    if not api_key.startswith("sk-or-v1-"):
        return False, "Invalid API key format. Must start with 'sk-or-v1-'"
    
    # Test the key by making a simple API call to OpenRouter
    url = f"{OPENROUTER_BASE_URL}/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return True, "API key is valid and working"
            elif response.status_code == 401:
                return False, "Invalid API key: Authentication failed"
            elif response.status_code == 403:
                return False, "API key is valid but access is forbidden"
            else:
                return False, f"API key test failed: HTTP {response.status_code}"
    
    except httpx.TimeoutException:
        return False, "API key test timed out. Please try again."
    except httpx.RequestError as e:
        return False, f"Network error while testing API key: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error while testing API key: {str(e)}"
