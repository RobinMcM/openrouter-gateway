"""
OpenRouter synchronous image generation client.

OpenRouter image generation uses the standard chat completions endpoint
with a `modalities` field. The response is synchronous — one POST, image
comes back as base64. No job_id, no polling.

Supported response shapes (OpenRouter returns one of these):
  1. data["images"][0]["url"]                              — top-level images array
  2. choices[0]["message"]["images"][0]["url"]             — images on message
  3. choices[0]["message"]["content"][0]["image_url"]["url"] — content array (OAI style)
"""

import os
import httpx
from typing import Optional

# Re-use the same key that the rest of the gateway uses.
# Raises RuntimeError at import time if not set — consistent with openrouter_client.py.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Models that use modalities=["image","text"] and support image_config.aspect_ratio.
# All other image models use modalities=["image"] only.
GEMINI_IMAGE_MODELS: frozenset = frozenset({
    "google/gemini-2.5-flash-image-preview",
    "google/gemini-3.1-flash-image-preview",
    "google/gemini-3-pro-image-preview",
})


def _extract_image_from_response(data: dict) -> tuple[str, str]:
    """
    Extract (b64_string, content_type) from an OpenRouter image response.

    Tries three known shapes in order. Raises ValueError if none match.
    """
    # Shape 1: top-level "images" array
    images = data.get("images")
    if isinstance(images, list) and images:
        return _parse_image_item(images[0])

    # Shape 2 + 3: dig into choices[0].message
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}

        # Shape 2: message.images[]
        msg_images = message.get("images")
        if isinstance(msg_images, list) and msg_images:
            return _parse_image_item(msg_images[0])

        # Shape 3: message.content[] with type="image_url"
        content = message.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    image_url_obj = item.get("image_url") or {}
                    url = image_url_obj.get("url") or ""
                    if url:
                        return _decode_data_url(url)

    raise ValueError(f"No image found in OpenRouter response. Keys present: {list(data.keys())}")


def _parse_image_item(item: dict) -> tuple[str, str]:
    """Parse a single image dict that has a 'url' key."""
    url = item.get("url") or ""
    if not url:
        raise ValueError(f"Image item has no 'url' field: {item}")
    return _decode_data_url(url)


def _decode_data_url(url: str) -> tuple[str, str]:
    """
    Split a data URL into (base64_payload, content_type).
    If it is not a data URL, treat it as a plain base64 string with image/png.
    """
    if url.startswith("data:"):
        # data:image/png;base64,<payload>
        header, _, payload = url.partition(",")
        mime = header.split(";")[0].replace("data:", "").strip()
        return payload, (mime or "image/png")
    # Plain base64 — no data: prefix
    return url, "image/png"


def generate_image_openrouter(
    prompt: str,
    model: str,
    aspect_ratio: str = "1:1",
    openrouter_api_key: Optional[str] = None,
) -> dict:
    """
    Generate an image via OpenRouter synchronously.

    Args:
        prompt:             Text prompt.
        model:              Full OpenRouter model ID (e.g. "black-forest-labs/flux.2-klein").
        aspect_ratio:       Aspect ratio string — only applied for Gemini models.
        openrouter_api_key: Override the module-level key (useful for testing).

    Returns:
        {
            "image_b64":    "<base64 string>",
            "content_type": "image/png",
            "model":        "<model id>",
        }

    Raises:
        httpx.HTTPStatusError: on non-2xx from OpenRouter.
        ValueError:            if the response contains no image.
    """
    api_key = openrouter_api_key or OPENROUTER_API_KEY
    is_gemini = model in GEMINI_IMAGE_MODELS

    modalities = ["image", "text"] if is_gemini else ["image"]

    payload: dict = {
        "model": model,
        "modalities": modalities,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    if is_gemini:
        payload["image_config"] = {"aspect_ratio": aspect_ratio}

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
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()

    image_b64, content_type = _extract_image_from_response(data)

    return {
        "image_b64": image_b64,
        "content_type": content_type,
        "model": model,
    }
