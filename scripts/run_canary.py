#!/usr/bin/env python3
"""
Gateway canary runner with readiness gating.

Reads .env values:
- GATEWAY_BASE_URL
- GATEWAY_INTERNAL_API_KEY
- GATEWAY_TIMEOUT_SECONDS

Behavior:
1) Wait until gateway is ready (/health + /api/instructions auth check)
2) Run deterministic canary sequence
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, Tuple
from urllib import error, request


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def api_call(
    base: str,
    path: str,
    timeout: int,
    method: str = "GET",
    body: Dict[str, Any] | None = None,
    api_key: str | None = None,
) -> Tuple[int, Dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Internal-API-Key"] = api_key
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(f"{base}{path}", method=method, headers=headers, data=data)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return response.status, (json.loads(payload) if payload else {})
    except error.HTTPError as exc:
        payload = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(payload) if payload else {}
        except Exception:
            parsed = {"raw": payload}
        return exc.code, parsed


def wait_until_ready(base: str, api_key: str, timeout: int, max_wait_seconds: int = 300) -> None:
    started = time.time()
    while True:
        health_code, _ = api_call(base, "/health", timeout, method="GET", api_key=None)
        auth_code, auth = api_call(base, "/api/instructions", timeout, method="GET", api_key=api_key)
        if health_code == 200 and auth_code == 200 and auth.get("status") == "ok":
            print("READY: gateway health and auth are both OK")
            return

        elapsed = int(time.time() - started)
        if elapsed >= max_wait_seconds:
            raise SystemExit(
                f"Gateway not ready after {max_wait_seconds}s: "
                f"health={health_code} auth={auth_code}"
            )
        print(f"WAITING ({elapsed}s): health={health_code} auth={auth_code}")
        time.sleep(3)


def main() -> int:
    load_env()
    base = os.getenv("GATEWAY_BASE_URL", "").rstrip("/")
    api_key = os.getenv("GATEWAY_INTERNAL_API_KEY", "")
    timeout = int(os.getenv("GATEWAY_TIMEOUT_SECONDS", "45"))
    if not base or not api_key:
        print("Missing GATEWAY_BASE_URL or GATEWAY_INTERNAL_API_KEY in environment.", file=sys.stderr)
        return 2

    wait_until_ready(base=base, api_key=api_key, timeout=timeout)

    # 1) instructions
    code, data = api_call(base, "/api/instructions", timeout, api_key=api_key)
    print("STEP instructions:", code, data.get("status"))
    if code != 200:
        return 1

    # 2) image model catalogue
    code, data = api_call(base, "/api/image/models", timeout, api_key=api_key)
    print("STEP image-models:", code, "count=", data.get("count"))
    if code != 200 or not isinstance(data.get("models"), list):
        return 1

    # 3) video model catalogue
    code, data = api_call(base, "/api/video/models", timeout, api_key=api_key)
    print("STEP video-models:", code, "count=", data.get("count"))
    if code != 200 or not isinstance(data.get("models"), list):
        return 1

    # 4) task list
    code, data = api_call(base, "/api/tasks", timeout, api_key=api_key)
    print("STEP tasks:", code, "count=", len(data.get("tasks", [])))
    if code != 200 or not isinstance(data.get("tasks"), list):
        return 1

    # 5) text execute (dry_run)
    execute_payload = {
        "provider": "openrouter",
        "job_type": "text-completion",
        "payload": {
            "model": "openai/gpt-4.1-mini",
            "messages": [{"role": "user", "content": "Say hello in one word."}],
        },
        "dry_run": True,
    }
    code, data = api_call(base, "/api/execute", timeout, method="POST", body=execute_payload, api_key=api_key)
    print("STEP text-execute:", code, data.get("status"))
    if code != 200:
        return 1

    # 6) image generate (dry_run)
    image_payload = {
        "model_key": "nano-banana",
        "prompt": "A dramatic sci-fi landscape",
        "aspect_ratio": "16:9",
        "dry_run": True,
    }
    code, data = api_call(base, "/api/image/generate", timeout, method="POST", body=image_payload, api_key=api_key)
    print("STEP image-generate (dry_run):", code, data.get("ok"))
    if code != 200 or not data.get("ok"):
        return 1

    # 7) video generate (dry_run)
    video_payload = {
        "model_key": "kling-v3-pro",
        "prompt": "Cinematic tracking shot through a forest",
        "duration": 5,
        "aspect_ratio": "16:9",
        "dry_run": True,
    }
    code, data = api_call(base, "/api/video/generate", timeout, method="POST", body=video_payload, api_key=api_key)
    print("STEP video-generate (dry_run):", code, data.get("ok"))
    if code != 200 or not data.get("ok"):
        return 1

    # 8) task execute (dry_run)
    task_payload = {
        "task": "generate-shot",
        "prompt": "Camera slowly pushes forward",
        "options": {"duration": 5, "aspect_ratio": "16:9"},
        "dry_run": True,
    }
    code, data = api_call(base, "/api/task/execute", timeout, method="POST", body=task_payload, api_key=api_key)
    print("STEP task-execute (dry_run):", code, data.get("ok"), "model=", data.get("resolved_model"))
    if code != 200 or not data.get("ok"):
        return 1

    print("\nAll canary steps passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
