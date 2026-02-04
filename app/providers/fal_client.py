"""
FAL.ai Client Module

Implements fal.ai API integration with:
- Correction #5: Auth headers + host allowlist for response URLs
- Correction #8: Robust result parsing for various output formats
- Support for sync and queue endpoints
- FAL queue status/result: use base model path (no subpath) per fal.ai docs
"""

import os
import httpx
from typing import Dict, Any, Tuple, Optional, List
from urllib.parse import urlparse
from app.logger import log_error, log_success


def model_id_for_queue_status(model_id: str) -> str:
    """
    Return the model_id to use for FAL queue status and result endpoints.

    Per fal.ai Queue API docs: "The subpath should be used when making the
    request, but not when getting request status or results." So we use the
    first two path segments (e.g. fal-ai/flux) for status/result, while
    submit uses the full model_id (e.g. fal-ai/flux/schnell).

    Examples:
        fal-ai/flux/schnell -> fal-ai/flux
        fal-ai/luma-dream-machine/ray-2-flash -> fal-ai/luma-dream-machine
        fal-ai/flux-pro -> fal-ai/flux-pro (unchanged)
    """
    parts = model_id.strip().split("/")
    if len(parts) <= 2:
        return model_id
    return "/".join(parts[:2])


# Environment configuration
FAL_KEY = os.getenv("FAL_KEY")
if not FAL_KEY:
    raise RuntimeError("FAL_KEY environment variable not set")

FAL_SYNC_BASE = os.getenv("FAL_SYNC_BASE", "https://fal.run")
FAL_QUEUE_BASE = os.getenv("FAL_QUEUE_BASE", "https://queue.fal.run")

# Correction #5: Host allowlist for response URL fetching
FAL_ALLOWED_HOSTS = {
    "fal.run",
    "queue.fal.run",
    "fal.media",
    "storage.googleapis.com",
    "v3.fal.media"
}


def _get_auth_headers() -> Dict[str, str]:
    """Get authorization headers for fal.ai API calls"""
    return {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json"
    }


def _validate_url_host(url: str) -> bool:
    """
    Validate that URL host is in allowlist (Correction #5).
    Returns True if valid, False otherwise.
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        
        # Check exact match or subdomain match
        for allowed_host in FAL_ALLOWED_HOSTS:
            if host == allowed_host or host.endswith(f".{allowed_host}"):
                return True
        
        return False
    
    except Exception:
        return False


async def submit_queue(model_id: str, payload: Dict[str, Any], webhook_url: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Submit job to fal.ai queue endpoint.
    
    Args:
        model_id: Model identifier (e.g., "fal-ai/flux/schnell")
        payload: Model-specific parameters
        webhook_url: Optional webhook URL for completion notification
    
    Returns:
        (success, request_id, error_message)
    """
    try:
        # Build URL with optional webhook query param (Correction: webhook is query param, not body)
        url = f"{FAL_QUEUE_BASE}/{model_id}"
        if webhook_url:
            url = f"{url}?fal_webhook={webhook_url}"
        
        headers = _get_auth_headers()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                request_id = data.get("request_id")
                
                if not request_id:
                    return False, None, "No request_id in fal.ai queue response"
                
                return True, request_id, None
            else:
                error_msg = f"fal.ai queue submit failed: {response.status_code} - {response.text[:500]}"
                return False, None, error_msg
    
    except httpx.TimeoutException:
        return False, None, "fal.ai queue submit timed out"
    except httpx.RequestError as e:
        return False, None, f"fal.ai queue submit request failed: {str(e)}"
    except Exception as e:
        return False, None, f"Unexpected error submitting to fal.ai queue: {str(e)}"


async def get_queue_status(
    model_id: str,
    request_id: str,
    job_id: Optional[str] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Check status of queued job.

    Uses base model path (no subpath) for the status URL per fal.ai Queue API:
    "The subpath should be used when making the request, but not when getting
    request status or results."

    Args:
        model_id: Full model identifier (e.g. fal-ai/flux/schnell)
        request_id: Request ID from submit_queue
        job_id: Optional gateway job_id for logging

    Returns:
        (success, status_data, error_message)

    Status data structure:
        {
            "status": "IN_QUEUE" | "IN_PROGRESS" | "COMPLETED",
            "response_url": "..." (when COMPLETED),
            "queue_position": N (when IN_QUEUE)
        }
    """
    status_model_id = model_id_for_queue_status(model_id)
    url = f"{FAL_QUEUE_BASE}/{status_model_id}/requests/{request_id}/status"
    try:
        headers = _get_auth_headers()

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return True, data, None
            else:
                # Correction #4: Transient errors should not fail the job
                error_msg = (
                    f"FAL status check {response.status_code} "
                    f"model_id={model_id} status_model_id={status_model_id}"
                )
                body_preview = (response.text or "")[:300]
                if body_preview:
                    error_msg = f"{error_msg} body={body_preview}"
                if job_id:
                    log_error(job_id, error_msg)
                return False, None, error_msg

    except (httpx.TimeoutException, httpx.RequestError) as e:
        # Correction #4: Network errors are transient
        error_msg = f"Transient error checking status: {type(e).__name__}"
        if job_id:
            log_error(job_id, error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error checking status: {str(e)}"
        if job_id:
            log_error(job_id, error_msg)
        return False, None, error_msg


async def fetch_queue_result(response_url: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch final result from response_url.
    
    Correction #5: Validates host and includes auth header.
    
    Args:
        response_url: URL returned by get_queue_status when COMPLETED
    
    Returns:
        (success, result_data, error_message)
    """
    try:
        # Correction #5: Validate host allowlist
        if not _validate_url_host(response_url):
            return False, None, f"Response URL host not in allowlist: {response_url}"
        
        # Correction #5: Include auth header when fetching result
        headers = _get_auth_headers()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(response_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return True, data, None
            else:
                error_msg = f"Failed to fetch result: {response.status_code} - {response.text[:500]}"
                return False, None, error_msg
    
    except httpx.TimeoutException:
        return False, None, "Result fetch timed out"
    except httpx.RequestError as e:
        return False, None, f"Result fetch request failed: {str(e)}"
    except Exception as e:
        return False, None, f"Unexpected error fetching result: {str(e)}"


async def call_sync(model_id: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Call fal.ai sync endpoint (blocks until completion).
    Use only for fast models (<10s).
    
    Args:
        model_id: Model identifier
        payload: Model-specific parameters
    
    Returns:
        (success, result_data, error_message)
    """
    try:
        url = f"{FAL_SYNC_BASE}/{model_id}"
        headers = _get_auth_headers()
        
        async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for sync
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return True, data, None
            else:
                error_msg = f"fal.ai sync call failed: {response.status_code} - {response.text[:500]}"
                return False, None, error_msg
    
    except httpx.TimeoutException:
        return False, None, "fal.ai sync call timed out"
    except httpx.RequestError as e:
        return False, None, f"fal.ai sync request failed: {str(e)}"
    except Exception as e:
        return False, None, f"Unexpected error calling fal.ai sync: {str(e)}"


def parse_fal_result(result_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse fal.ai result into standardized format.
    
    Correction #8: Handle multiple output shapes gracefully.
    
    Common output patterns:
    - images: [{"url": "...", "width": N, "height": N}]
    - video: {"url": "..."}
    - videos: [{"url": "..."}]
    - audio_file: {"url": "..."}
    - audio: {"url": "..."}
    
    Returns:
        {
            "files": [{"url": "...", "content_type": "...", ...}],
            "raw": {...}  # Original response for unknown formats
        }
    """
    files = []
    
    # Try images (list)
    if "images" in result_data and isinstance(result_data["images"], list):
        for img in result_data["images"]:
            if isinstance(img, dict) and "url" in img:
                files.append({
                    "url": img["url"],
                    "content_type": "image/jpeg",  # Default, may vary
                    "width": img.get("width"),
                    "height": img.get("height")
                })
    
    # Try image (single)
    elif "image" in result_data and isinstance(result_data["image"], dict):
        img = result_data["image"]
        if "url" in img:
            files.append({
                "url": img["url"],
                "content_type": "image/jpeg",
                "width": img.get("width"),
                "height": img.get("height")
            })
    
    # Try video (single)
    if "video" in result_data and isinstance(result_data["video"], dict):
        vid = result_data["video"]
        if "url" in vid:
            files.append({
                "url": vid["url"],
                "content_type": "video/mp4"
            })
    
    # Try videos (list - Correction #8)
    elif "videos" in result_data and isinstance(result_data["videos"], list):
        for vid in result_data["videos"]:
            if isinstance(vid, dict) and "url" in vid:
                files.append({
                    "url": vid["url"],
                    "content_type": "video/mp4"
                })
    
    # Try audio_file or audio (Correction #8: alternative keys)
    audio = result_data.get("audio_file") or result_data.get("audio")
    if audio and isinstance(audio, dict) and "url" in audio:
        files.append({
            "url": audio["url"],
            "content_type": "audio/mpeg"
        })
    
    # Return parsed files + raw data (Correction #8: keep raw for unknown formats)
    return {
        "files": files,
        "raw": result_data  # Preserve original for MovieShaker to handle edge cases
    }
