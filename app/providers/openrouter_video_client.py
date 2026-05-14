"""
OpenRouter synchronous video generation client.

OpenRouter video generation uses the standard chat completions endpoint
with modalities=["video"]. The response is synchronous — one POST, video
URL comes back in the response. No job_id, no polling.

For image-to-video models, pass source_image as a URL; it is included in
the messages content array as an image_url item alongside the text prompt.

Supported response shapes (OpenRouter may return one of these):
  1. data[0]["url"]                                — top-level data array
  2. choices[0]["message"]["content"][0]["video_url"]["url"]  — content array
  3. choices[0]["message"]["video_url"]            — video_url on message
"""

import os
import httpx
from typing import Optional

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


def _extract_video_from_response(data: dict) -> tuple[str, str]:
    """
    Extract (video_url, content_type) from an OpenRouter video response.

    Tries known response shapes. Raises ValueError if none match.
    """
    # Shape 1: top-level "data" array (generation-style)
    top_data = data.get("data")
    if isinstance(top_data, list) and top_data:
        item = top_data[0]
        url = item.get("url") or item.get("video_url") or ""
        if url:
            return url, "video/mp4"

    # Shape 2 + 3: dig into choices[0].message
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}

        # Shape 2: message.content[] with type="video_url"
        content = message.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "video_url":
                    video_url_obj = item.get("video_url") or {}
                    url = video_url_obj.get("url") or ""
                    if url:
                        return url, "video/mp4"

        # Shape 3: message.video_url directly
        video_url = message.get("video_url")
        if isinstance(video_url, dict):
            url = video_url.get("url") or ""
            if url:
                return url, "video/mp4"
        elif isinstance(video_url, str) and video_url:
            return video_url, "video/mp4"

    raise ValueError(f"No video found in OpenRouter response. Keys present: {list(data.keys())}")


def generate_video_openrouter(
    prompt: str,
    model: str,
    source_image: Optional[str] = None,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    openrouter_api_key: Optional[str] = None,
) -> dict:
    """
    Generate a video via OpenRouter synchronously.

    Args:
        prompt:             Text prompt.
        model:              Full OpenRouter model ID (e.g. "kwaivgi/kling-v3.0-pro").
        source_image:       Optional image URL for image-to-video generation.
        duration:           Duration in seconds.
        aspect_ratio:       Aspect ratio string (e.g. "16:9", "9:16", "1:1").
        openrouter_api_key: Override the module-level key (useful for testing).

    Returns:
        {
            "video_url":    "<url string>",
            "content_type": "video/mp4",
            "model":        "<model id>",
        }

    Raises:
        httpx.HTTPStatusError: on non-2xx from OpenRouter.
        ValueError:            if the response contains no video.
    """
    api_key = openrouter_api_key or OPENROUTER_API_KEY

    messages_content: list = []
    if source_image:
        messages_content.append({
            "type": "image_url",
            "image_url": {"url": source_image},
        })
    messages_content.append({"type": "text", "text": prompt})

    payload: dict = {
        "model": model,
        "modalities": ["video"],
        "messages": [
            {"role": "user", "content": messages_content}
        ],
        "video_config": {
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://movieshaker.com",
        "X-Title": "MovieShaker",
    }

    response = httpx.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=300.0,
    )
    response.raise_for_status()
    data = response.json()

    video_url, content_type = _extract_video_from_response(data)

    return {
        "video_url": video_url,
        "content_type": content_type,
        "model": model,
    }
