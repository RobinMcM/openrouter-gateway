# OpenRouter Gateway

Stateless AI execution gateway for MovieShaker and RapidMVP apps.
Routes requests to OpenRouter (text) or FAL.ai (image/video/audio)
and returns results with per-request cost information.

**The gateway does not track user billing.** Cost attribution is handled
by the calling service.

## Providers

| Provider | Media Types | Execution |
|----------|-------------|-----------|
| OpenRouter | text-completion, text-generation | Synchronous |
| FAL.ai | image-generation, image-to-video, video-generation, audio-generation | Asynchronous (queue) |

## Setup

### Environment Variables

**Required:**
```bash
INTERNAL_API_KEY=your-secret-internal-key
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key
FAL_KEY=your-fal-key
```

**Optional:**
```bash
ADMIN_API_KEY=your-admin-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
FAL_SYNC_BASE=https://fal.run
FAL_QUEUE_BASE=https://queue.fal.run
ADMIN_MARKUP_PERCENT=0.10
ADMIN_FIXED_FEE=0.001
```

### Local Development

```bash
pip install -r requirements.txt
export INTERNAL_API_KEY=test-key
export OPENROUTER_API_KEY=sk-or-v1-xxx
export FAL_KEY=your-fal-key
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t openrouter-gateway .
docker run -d -p 8000:8000 \
  -e INTERNAL_API_KEY=your-secret-key \
  -e OPENROUTER_API_KEY=sk-or-v1-xxx \
  -e FAL_KEY=your-fal-key \
  openrouter-gateway
```

## Authentication

All `/api/*` endpoints require:
```
X-Internal-API-Key: your-secret-key
```

Only `GET /health` is unauthenticated.
`GET /api/logs` and config endpoints require `ADMIN_API_KEY` if set.

## API Endpoints

### Health
```bash
curl http://localhost:8000/health
# → {"status": "healthy"}
```

### Text Completion (OpenRouter — synchronous)
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

### Media Generation (FAL.ai — asynchronous)
```bash
# Submit job
curl -X POST http://localhost:8000/api/media/execute \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "fal",
    "query_type": "image-video",
    "model": "fal-ai/veo3/image-to-video",
    "source_image": "https://example.com/image.jpg",
    "options": { "duration": "6s" },
    "dry_run": false
  }'
# → { "job_id": "abc-123", "job_status": "queued", ... }

# Poll for result
curl -H "X-Internal-API-Key: your-key" \
  http://localhost:8000/api/status/abc-123
# → { "job_status": "completed", "result": { "files": [...] }, "usage": {...} }
```

### Cost Estimate (no provider call)
```bash
curl -X POST http://localhost:8000/api/route \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{ "job_type": "text-completion", "input_data": { "prompt": "Hello" } }'
```

### Available Models
```bash
# OpenRouter text models
curl -H "X-Internal-API-Key: your-key" http://localhost:8000/api/models

# FAL media models
curl -H "X-Internal-API-Key: your-key" http://localhost:8000/api/media/models

# FAL media models filtered by type
curl -H "X-Internal-API-Key: your-key" \
  "http://localhost:8000/api/media/models?media_type=image-to-video"
```

## Async Job Lifecycle (FAL.ai)

```
POST /api/execute or /api/media/execute
  → job_id returned immediately, job_status: "queued"

GET /api/status/{job_id}   ← poll until completed or failed
  → job_status: "processing"
  → job_status: "completed" + result + usage
  → job_status: "failed" + error

GET /api/result/{job_id}   ← fetch result directly
```

Job state is held in Valkey — transient, not for billing.
The calling service must persist results and costs.

## Canary Testing

```bash
# Requires .env with GATEWAY_BASE_URL and GATEWAY_INTERNAL_API_KEY
python3 scripts/run_canary.py
```

Waits for `/health` and `/api/instructions` before running smoke tests.

## Security

- `INTERNAL_API_KEY`, `OPENROUTER_API_KEY`, `FAL_KEY` are never logged
- FAL response URL host is validated against an allowlist before fetching
- CORS is handled by Nginx — not in FastAPI application code
- Service fails fast on startup if required env vars are missing

## Deployment

Deployed at `https://models.rapidmvp.io` on a DigitalOcean Droplet.
HTTPS and CORS managed by Nginx — see `nginx/conf.d/models.rapidmvp.io.conf`.

See `DEPLOYMENT.md` for full deployment runbook.
