import os
import hmac
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)

# Fail fast if INTERNAL_API_KEY not set
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
if not INTERNAL_API_KEY:
    raise RuntimeError("INTERNAL_API_KEY environment variable not set")

# Correction #10: Optional admin key for sensitive endpoints like /api/logs
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")  # Optional, falls back to INTERNAL_API_KEY


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify API key using timing-attack resistant comparison.
    Returns 401 with exact error messages matching ffmpeg-api pattern.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    # Use hmac.compare_digest for timing-attack resistance
    if not hmac.compare_digest(api_key, INTERNAL_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key


async def verify_admin_key(api_key: str = Security(api_key_header)):
    """
    Verify admin API key for sensitive endpoints (Correction #10).
    Falls back to INTERNAL_API_KEY if ADMIN_API_KEY not set.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    # Use admin key if configured, otherwise fall back to internal key
    required_key = ADMIN_API_KEY if ADMIN_API_KEY else INTERNAL_API_KEY
    
    if not hmac.compare_digest(api_key, required_key):
        raise HTTPException(status_code=401, detail="Invalid or insufficient API key")
    
    return api_key
