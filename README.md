# OpenRouter Gateway

Stateless AI execution gateway for MovieShaker and RapidMVP apps.
Routes requests to OpenRouter (text, synchronous image, synchronous video)
and returns results with per-request cost information.

**The gateway does not track user billing.** Cost attribution is handled
by the calling service.

## Providers

| Provider | Media Types | Execution |
|----------|-------------|-----------|
| OpenRouter | text-completion, text-generation | Synchronous |
| OpenRouter | image-generation (via `/api/image/generate`) | Synchronous — returns base64 |
| OpenRouter | video-generation (via `/api/video/generate`) | Synchronous — returns URL |

## Setup

### Environment Variables

**Required:**
```bash
INTERNAL_API_KEY=your-secret-internal-key
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key
```

**Optional:**
```bash
ADMIN_API_KEY=your-admin-key          # gates /api/logs; falls back to INTERNAL_API_KEY
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
ADMIN_MARKUP_PERCENT=0.10
ADMIN_FIXED_FEE=0.001
ROUTING_CONFIG_JSON='{...}'           # override routing config inline
ROUTING_CONFIG_PATH=/path/to/file     # override routing config from file
PRICING_CONFIG_JSON='{...}'           # override pricing config inline
PRICING_CONFIG_PATH=/path/to/file     # override pricing config from file
```

### Local Development

```bash
pip install -r requirements.txt
export INTERNAL_API_KEY=test-key
export OPENROUTER_API_KEY=sk-or-v1-xxx
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t openrouter-gateway .
docker run -d -p 8000:8000 \
  -e INTERNAL_API_KEY=your-secret-key \
  -e OPENROUTER_API_KEY=sk-or-v1-xxx \
  openrouter-gateway
```

## Authentication

All `/api/*` endpoints require:
```
X-Internal-API-Key: your-secret-key
```

Only `GET /health` and the HTML pages (`/models`, `/models-showcase`, `/config`)
are unauthenticated.
`GET /api/logs` requires `ADMIN_API_KEY` if set, otherwise `INTERNAL_API_KEY`.

## API Endpoints

### Unauthenticated

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/models` | HTML: OpenRouter model showcase page |
| GET | `/models-showcase` | HTML: MovieShaker AI tools showcase page |
| GET | `/config` | HTML: Owner config page (update OpenRouter key) |

### Authenticated (`X-Internal-API-Key`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/instructions` | Full API documentation |
| GET | `/api/logs` | Sanitised logs (admin only) |
| POST | `/api/route` | Cost estimate only — no provider call |
| POST | `/api/execute` | OpenRouter text completion |
| GET | `/api/models` | OpenRouter text model list |
| GET | `/api/models-showcase` | MovieShaker model showcase (JSON) |
| GET | `/api/image/models` | OpenRouter image model catalogue |
| POST | `/api/image/generate` | OpenRouter synchronous image generation (returns base64) |
| GET | `/api/video/models` | OpenRouter video model catalogue |
| POST | `/api/video/generate` | OpenRouter synchronous video generation (returns URL) |
| GET | `/api/tasks` | Task catalogue with resolved models |
| POST | `/api/task/execute` | Resolve task → model → dispatch to image or video |
| POST | `/api/classify` | Classify a user message to the appropriate MovieShaker agent |

### Admin only

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/openrouter-key/status` | OpenRouter key config status |
| POST | `/api/config/openrouter-key` | Update OpenRouter key at runtime |
| POST | `/api/config/test-openrouter-key` | Test an OpenRouter key |

---

## Health

```bash
curl http://localhost:8000/health
# → {"status": "healthy"}
```

---

## Text Completion (OpenRouter — synchronous)

```bash
curl -X POST http://localhost:8000/api/execute \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openrouter",
    "job_type": "text-completion",
    "payload": {
      "model": "openai/gpt-4.1-mini",
      "messages": [{"role": "user", "content": "Hello!"}]
    },
    "dry_run": false
  }'
```

Response:
```json
{
  "status": "ok",
  "routing": { "provider": "openrouter", "model": "openai/gpt-4.1-mini" },
  "result": { "choices": [{ "message": { "content": "Hello there!" } }] },
  "usage": { "input_tokens": 8, "output_tokens": 5, "total_cost": 0.00054 }
}
```

---

## OpenRouter Synchronous Image Generation

Returns a base64-encoded image immediately (no polling required).

```bash
# List available models
curl -H "X-Internal-API-Key: your-key" \
  http://localhost:8000/api/image/models
```

```bash
# Generate image
curl -X POST http://localhost:8000/api/image/generate \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "nano-banana",
    "prompt": "A film noir detective office",
    "aspect_ratio": "16:9",
    "dry_run": false
  }'
```

Response:
```json
{
  "ok": true,
  "image_b64": "iVBORw0KGgo...",
  "content_type": "image/png",
  "model": "google/gemini-2.5-flash-image",
  "model_key": "nano-banana",
  "dry_run": false
}
```

Available `model_key` values (from `/api/image/models`):

| model_key | Model | Best For |
|-----------|-------|---------|
| `flux-2-pro` | black-forest-labs/flux.2-pro | Moodboard cinematic passes |
| `flux-2-flex` | black-forest-labs/flux.2-flex | Artifacts with text, inserts |
| `flux-2-klein` | black-forest-labs/flux.2-klein | Quick drafts |
| `nano-banana` | google/gemini-2.5-flash-image | Backgrounds, scene objects |
| `nano-banana-2` | google/gemini-3.1-flash-image-preview | Character references |
| `nano-banana-pro` | google/gemini-3-pro-image-preview | Final quality images |
| `gpt-5-image` | openai/gpt-5-image | Final reference shots (Visualize) |
| `gpt-5-image-mini` | openai/gpt-5-image-mini | Quick high quality previews |
| `gpt-5-4-image` | openai/gpt-5.4-image-2 | Highest fidelity reference shots |

Default: `flux-2-pro`

---

## OpenRouter Synchronous Video Generation

Returns a video URL immediately (no polling required). Supports text-to-video
and image-to-video via `source_image`.

```bash
# List available models
curl -H "X-Internal-API-Key: your-key" \
  http://localhost:8000/api/video/models
```

```bash
# Text-to-video
curl -X POST http://localhost:8000/api/video/generate \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "kling-v3-pro",
    "prompt": "Cinematic tracking shot through a forest at golden hour",
    "duration": 5,
    "aspect_ratio": "16:9",
    "dry_run": false
  }'
```

```bash
# Image-to-video
curl -X POST http://localhost:8000/api/video/generate \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "kling-v3-pro",
    "prompt": "Camera slowly pushes forward",
    "source_image": "https://example.com/frame.jpg",
    "duration": 5,
    "aspect_ratio": "16:9",
    "dry_run": false
  }'
```

Response:
```json
{
  "ok": true,
  "video_url": "https://openrouter.ai/...",
  "content_type": "video/mp4",
  "model": "kwaivgi/kling-v3.0-pro",
  "model_key": "kling-v3-pro",
  "dry_run": false
}
```

Available `model_key` values (from `/api/video/models`):

| model_key | Model | Duration | Cost/s | Recommended |
|-----------|-------|----------|--------|-------------|
| `kling-v3-pro` | kwaivgi/kling-v3.0-pro | 3–15s | $0.168 | ✓ |
| `sora-2-pro` | openai/sora-2-pro | 5–20s | $0.30 | ✓ |
| `veo-3-1` | google/veo-3.1 | 5–30s | $0.40 | ✓ |
| `veo-3-1-fast` | google/veo-3.1-fast | 5–30s | $0.20 | |
| `hailuo-2-3` | minimax/hailuo-2.3 | 3–10s | $0.15 | |
| `wan-2-7` | alibaba/wan-2.7 | 3–10s | $0.08 | |
| `seedance-2` | bytedance/seedance-2.0 | 3–10s | $0.10 | |
| `kling-video-o1` | kwaivgi/kling-video-o1 | 5–10s | $0.20 | |

Default: `kling-v3-pro`

---

## Task Execute

Resolve a task name to the best available model and dispatch. Use this when
the caller wants the gateway to make the model selection autonomously.

```bash
# List available tasks
curl -H "X-Internal-API-Key: your-key" \
  http://localhost:8000/api/tasks
```

```bash
# Execute a task
curl -X POST http://localhost:8000/api/task/execute \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "generate-shot",
    "source": "https://example.com/frame.jpg",
    "prompt": "Camera slowly pushes forward",
    "options": { "duration": 5, "aspect_ratio": "16:9" },
    "dry_run": false
  }'
```

Response:
```json
{
  "ok": true,
  "task": "generate-shot",
  "resolved_model": "kling-v3-pro",
  "endpoint": "video",
  "dry_run": false,
  "result": { "video_url": "https://...", "content_type": "video/mp4" }
}
```

Available tasks: `generate-shot`, `generate-image`

---

## Agent Classification

Classifies a user message to the correct MovieShaker agent. Uses page path and
context mode rules first (no LLM call); falls back to Gemini Flash only for
ambiguous cases.

```bash
curl -X POST http://localhost:8000/api/classify \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many shooting days do we need?",
    "page_path": "/scheduling",
    "context_mode": "scheduling"
  }'
```

Response:
```json
{
  "agent": "coproducer",
  "confidence": 0.95,
  "reasoning": "Page context: /scheduling"
}
```

Agents: `cowriter`, `coproducer`, `codirector`, `codesigner`

---

## Cost Estimate (no provider call)

```bash
curl -X POST http://localhost:8000/api/route \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{ "job_type": "text-completion", "input_data": { "prompt": "Hello" } }'
```

---

## Available Models

```bash
# OpenRouter text models
curl -H "X-Internal-API-Key: your-key" http://localhost:8000/api/models

# OpenRouter image models
curl -H "X-Internal-API-Key: your-key" http://localhost:8000/api/image/models

# OpenRouter video models
curl -H "X-Internal-API-Key: your-key" http://localhost:8000/api/video/models
```

---

## Canary Testing

```bash
# Requires .env with GATEWAY_BASE_URL and GATEWAY_INTERNAL_API_KEY
python3 scripts/run_canary.py
```

Waits for `/health` and `/api/instructions` before running smoke tests.

---

## Security

- `INTERNAL_API_KEY` and `OPENROUTER_API_KEY` are never logged
- CORS is handled by Nginx — not in FastAPI application code
- Service fails fast on startup if required env vars are missing
- Model override requests are validated against the model catalogue

---

## Deployment

Deployed at `https://models.rapidmvp.io` on a DigitalOcean Droplet.
HTTPS and CORS managed by Nginx — see `nginx/conf.d/models.rapidmvp.io.conf`.

See `DEPLOYMENT.md` for the full deployment runbook.
