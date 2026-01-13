import os
import hmac
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)

# Fail fast if INTERNAL_API_KEY not set
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
if not INTERNAL_API_KEY:
    raise RuntimeError("INTERNAL_API_KEY environment variable not set")


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
