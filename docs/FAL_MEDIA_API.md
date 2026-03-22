# FAL Media API – Client reference

This document is the **authoritative specification** for calling the OpenRouter Gateway’s FAL media endpoints. Use it to implement any client (e.g. testopenrouter, MovieShaker, or a new app). The testopenrouter app is a reference implementation that validates this API.

## Overview

FAL media generation is **asynchronous**:

1. **Submit** a job with `POST /api/execute` (provider `fal`).
2. **Poll** `GET /api/status/{job_id}` until `job_status` is `completed` or `failed`.
3. On **completion**, use `result.files[].url` (and optionally `usage`).

## Authentication

All requests must include the gateway’s internal API key:

- **Header:** `X-Internal-API-Key: <your-gateway-api-key>`
- The key is configured on the gateway (e.g. `INTERNAL_API_KEY`). Obtain it from your gateway administrator.

## Base URL

- **Production example:** `https://models.rapidmvp.io`
- Base URL is deployment-specific; use the URL where the OpenRouter Gateway is hosted.

---

## POST /api/execute (FAL)

Submit a FAL media generation job. Returns immediately with a gateway `job_id`; the job runs asynchronously.

### Request

- **Method:** `POST`
- **Path:** `/api/execute`
- **Headers:** `Content-Type: application/json`, `X-Internal-API-Key: <key>`

**Body (JSON):**

| Field        | Type    | Required | Description |
|-------------|---------|----------|-------------|
| `provider`  | string  | Yes      | Must be `"fal"`. |
| `media_type`| string  | Yes      | One of: `image-generation`, `image-generation-hd`, `video-generation`, `image-to-video`, `audio-generation`. |
| `model`     | string  | No       | Override default model for `media_type`. Must be in the gateway’s allowlist (see [FAL_GATEWAY_README.md](../FAL_GATEWAY_README.md)). |
| `payload`   | object  | Yes      | Model-specific parameters (see below). |
| `dry_run`   | boolean | No       | If `true`, no job is submitted; response includes estimate only. Default `false`. |
| `webhook_url` | string | No     | Optional webhook URL for completion notification. |

**Example – image generation:**

```json
{
  "provider": "fal",
  "media_type": "image-generation",
  "payload": {
    "prompt": "A beautiful sunset over the ocean",
    "image_size": "square_hd",
    "num_images": 1
  },
  "dry_run": false
}
```

**Example – video generation:**

```json
{
  "provider": "fal",
  "media_type": "video-generation",
  "payload": {
    "prompt": "A cat walking in the rain",
    "aspect_ratio": "16:9"
  },
  "dry_run": false
}
```

### Response (success, 200)

| Field         | Type   | Description |
|---------------|--------|-------------|
| `ok`          | boolean | `true`. |
| `job_id`      | string | Gateway job ID. Use this for status polling. |
| `job_status`  | string | Usually `"processing"` (or `"completed"` for dry run). |
| `status_url`  | string | Path to poll, e.g. `"/api/status/{job_id}"`. Resolve against base URL. |
| `estimate`    | object | Cost estimate: `total`, `estimated`, `pricing_version`, etc. |

**Example:**

```json
{
  "ok": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_status": "processing",
  "status_url": "/api/status/550e8400-e29b-41d4-a716-446655440000",
  "estimate": {
    "total": 0.0043,
    "estimated": true,
    "pricing_version": "2026-01-22",
    "strategy": "per_megapixel"
  }
}
```

### Response (error)

- **4xx/5xx** or body with `status: "error"` and `message`. Example: invalid `media_type`, model not allowed, or FAL submission failure.

---

## GET /api/status/{job_id}

Get the current status and, when completed, the result and usage.

### Request

- **Method:** `GET`
- **Path:** `/api/status/{job_id}` where `job_id` is the value from the submit response.
- **Headers:** `X-Internal-API-Key: <key>`

### Response (200) – common fields

| Field             | Type   | Description |
|-------------------|--------|-------------|
| `ok`              | boolean | `true` for completed/success; `false` for failed. |
| `job_id`          | string | Same as requested `job_id`. |
| `job_status`      | string | `"queued"` \| `"processing"` \| `"completed"` \| `"failed"`. |
| `result`          | object | Present when `job_status === "completed"`. See below. |
| `usage`           | object | Present when completed; cost info (e.g. `total`, `estimated`). |
| `error`           | string | Present when `job_status === "failed"`. |
| `warning`         | string | Optional; e.g. transient status-check failure. Client should retry. |
| `provider_status` | object | Optional; raw FAL status when still in progress. |

### When `job_status === "completed"`

- **`result`** (object):
  - **`result.files`** (array): List of generated assets.
    - Each item: `url` (string), `content_type` (string), optional `width`, `height`.
  - **`result.raw`** (object): Original FAL response for debugging or custom handling.
- **`usage`** (object): e.g. `total` (number), `estimated` (boolean).

**Example:**

```json
{
  "ok": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_status": "completed",
  "result": {
    "files": [
      {
        "url": "https://fal.media/files/abc123.png",
        "content_type": "image/png",
        "width": 1024,
        "height": 1024
      }
    ],
    "raw": { }
  },
  "usage": {
    "total": 0.0043,
    "estimated": false
  }
}
```

### When `job_status === "processing"` or `"queued"`

- `result` and `usage` are absent or null.
- Optional `warning` (e.g. transient error checking FAL): client should retry the same `GET /api/status/{job_id}` after a short delay (e.g. 2 seconds).

### When `job_status === "failed"`

- **`error`** (string): Human-readable failure reason.
- **`ok`**: `false`.

**Example:**

```json
{
  "ok": false,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_status": "failed",
  "error": "FAL API error: ..."
}
```

### Errors (4xx/5xx)

- **404:** Job not found (wrong `job_id` or job expired/TTL).
- **401/403:** Invalid or missing `X-Internal-API-Key`.

---

## Client flow (step-by-step)

1. **Submit:** `POST /api/execute` with `provider: "fal"`, `media_type`, and `payload`. Read `job_id` from the response.
2. **Poll:** `GET /api/status/{job_id}` on an interval (e.g. every 2 seconds).
3. **Decide:**
   - If `job_status === "completed"`: use `result.files[].url` (and optionally `usage`). Stop polling.
   - If `job_status === "failed"`: use `error` and stop.
   - If `job_status === "queued"` or `"processing"`: continue polling. If `warning` is set, still retry; the job may complete on the next poll.
4. **Timeout:** Recommend a client-side timeout (e.g. 6–10 minutes). If reached, treat as failure or offer a “check again” action that polls once more.

---

## Media types and default models

| media_type            | Default model (approximate)        | Typical use        |
|-----------------------|------------------------------------|--------------------|
| `image-generation`    | fal-ai/flux/schnell                | Fast image         |
| `image-generation-hd` | fal-ai/flux-pro                    | HD image           |
| `video-generation`    | fal-ai/luma-dream-machine/ray-2-flash | Text-to-video   |
| `image-to-video`      | fal-ai/kling-video/...             | Image-to-video     |
| `audio-generation`    | fal-ai/stable-audio                | Audio/music        |

Exact defaults and allowlist are in the gateway (e.g. `app/routing/media_routing.py` and [FAL_GATEWAY_README.md](../FAL_GATEWAY_README.md)).

---

## cURL examples

**Submit job:**

```bash
curl -X POST "https://models.rapidmvp.io/api/execute" \
  -H "X-Internal-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "fal",
    "media_type": "image-generation",
    "payload": {
      "prompt": "A beautiful sunset",
      "image_size": "square_hd"
    },
    "dry_run": false
  }'
```

**Poll status (replace JOB_ID):**

```bash
curl -s "https://models.rapidmvp.io/api/status/JOB_ID" \
  -H "X-Internal-API-Key: YOUR_KEY" | jq
```

**Poll until completed (bash):**

```bash
JOB_ID="<from-submit-response>"
while true; do
  STATUS=$(curl -s "https://models.rapidmvp.io/api/status/$JOB_ID" \
    -H "X-Internal-API-Key: YOUR_KEY" | jq -r '.job_status')
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] && break
  [ "$STATUS" = "failed" ] && break
  sleep 2
done
curl -s "https://models.rapidmvp.io/api/status/$JOB_ID" -H "X-Internal-API-Key: YOUR_KEY" | jq
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|--------|----------------|--------|
| 401 / 403 | Wrong or missing API key | Check `X-Internal-API-Key` and gateway config. |
| 404 on status | Invalid or expired `job_id` | Ensure you use the `job_id` from the submit response; jobs have a TTL (e.g. 1 hour). |
| `job_status` always `processing` + `warning` | Transient errors talking to FAL | Keep polling; gateway retries. If it persists, check gateway logs for “FAL status check” / “Transient status error”. |
| Job fails on FAL | See `error` in response | Inspect `error`; check FAL quota, model, and payload. |

---

## Gateway implementation note (for maintainers)

The gateway calls FAL’s queue **status** (and result) endpoints using a **base model path** (no subpath), per fal.ai docs: “The subpath should be used when making the request, but not when getting request status or results.” The normalization is in `app/providers/fal_client.py` (`model_id_for_queue_status`). Submit continues to use the full `model_id` (including subpath).
