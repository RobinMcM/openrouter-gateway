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
        health_code, health = api_call(base, "/health", timeout, method="GET", api_key=None)
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

    # 2) models query
    code, data = api_call(base, "/api/media/models?query_type=image-video", timeout, api_key=api_key)
    print("STEP media-models:", code, "count=", data.get("count"))
    if code != 200 or not isinstance(data.get("models"), list):
        return 1

    # 3) submit generic request with unknown field (must be dropped)
    execute_payload = {
        "query_type": "text-image",
        "model": "fal-ai/flux/schnell",
        "options": {
            "prompt": "A dramatic sci-fi landscape with a single ship",
            "aspect_ratio": "16:9",
            "unknown_extra_field": "drop-me",
        },
        "destination": {
            "target": "digitalocean-spaces",
            "bucket": "movieshaker-indie",
            "path_prefix": "canary/gateway-final-phase",
        },
        "dry_run": False,
    }
    code, data = api_call(base, "/api/execute", timeout, method="POST", body=execute_payload, api_key=api_key)
    print("STEP execute:", code, data.get("job_status"), "stage=", data.get("stage"))
    job_id = data.get("job_id")
    if code != 200 or not job_id:
        return 1

    # 4) poll status
    terminal = {"completed", "failed"}
    status_payload: Dict[str, Any] = {}
    for _ in range(90):
        code, status_payload = api_call(base, f"/api/status/{job_id}", timeout, api_key=api_key)
        job_status = status_payload.get("job_status")
        print("STEP status:", code, job_status, "stage=", status_payload.get("stage"))
        if job_status in terminal:
            break
        time.sleep(2)

    # 5) result
    code, result_payload = api_call(base, f"/api/result/{job_id}", timeout, api_key=api_key)
    print("STEP result:", code, result_payload.get("job_status"), "stage=", result_payload.get("stage"))
    print(
        "TRACE:",
        {
            "accepted_fields": result_payload.get("accepted_fields"),
            "dropped_fields": result_payload.get("dropped_fields"),
            "stage_history": result_payload.get("stage_history"),
        },
    )

    if code != 200 or result_payload.get("job_status") != "completed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
