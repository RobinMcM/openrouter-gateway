# OpenRouter Gateway

Internal-only microservice for OpenRouter model routing, cost estimation, and execution.

## Overview

This service provides a simplified interface to OpenRouter's API with:
- Intelligent model routing based on job type
- Cost estimation before execution
- Admin markup calculation
- Comprehensive logging with secret sanitization
- Timing-attack resistant authentication

## Architecture

- **Language**: Python 3.11
- **Framework**: FastAPI + Pydantic
- **HTTP Client**: httpx (async)
- **Authentication**: Single API key with `hmac.compare_digest`
- **Logging**: Structured logs to `/tmp/openrouter-gateway.log`

## Setup

### Environment Variables

**Required** (service fails fast if missing):
```bash
INTERNAL_API_KEY=your-secret-internal-key
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key
```

**Optional**:
```bash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
ADMIN_MARKUP_PERCENT=0.10
ADMIN_FIXED_FEE=0.001
```

### Docker Build & Run

```bash
# Build image
docker build -t openrouter-gateway .

# Run container
docker run -d \
  -p 8000:8000 \
  -e INTERNAL_API_KEY=your-secret-key \
  -e OPENROUTER_API_KEY=sk-or-v1-xxx \
  openrouter-gateway
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export INTERNAL_API_KEY=test-key
export OPENROUTER_API_KEY=sk-or-v1-xxx

# Run service
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### `GET /health`
Unauthenticated health check.

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "healthy"}
```

### `GET /api/instructions`
Get API documentation and endpoint schemas.

```bash
curl -H "X-Internal-API-Key: your-key" \
  http://localhost:8000/api/instructions
```

### `GET /api/logs?lines=200`
Get recent operational logs (sanitized).

```bash
curl -H "X-Internal-API-Key: your-key" \
  "http://localhost:8000/api/logs?lines=100"
```

Response:
```json
{
  "status": "ok",
  "lines": 100,
  "logs": ["2026-01-13T10:30:00Z INFO job=abc123 endpoint=route status=started", "..."]
}
```

### `POST /api/route`
Get routing decision and cost estimate (does NOT call OpenRouter).

```bash
curl -X POST http://localhost:8000/api/route \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "text-completion",
    "input_data": {
      "prompt": "Hello, how are you?",
      "max_tokens": 100
    }
  }'
```

Response:
```json
{
  "status": "ok",
  "routing": {
    "provider": "openai",
    "model": "gpt-4",
    "endpoint": "/chat/completions"
  },
  "estimate": {
    "input_tokens": 5,
    "output_tokens": 100,
    "input_cost": 0.00015,
    "output_cost": 0.006,
    "subtotal": 0.00615,
    "admin_markup_percent": 0.10,
    "admin_markup_fixed": 0.001,
    "admin_total": 0.001615,
    "total": 0.007765,
    "estimated": true
  }
}
```

### `POST /api/execute`
Execute OpenRouter API call or dry-run.

**Dry Run Example** (no OpenRouter call):
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "text-completion",
    "payload": {
      "model": "gpt-4",
      "messages": [{"role": "user", "content": "Hello!"}]
    },
    "dry_run": true
  }'
```

**Execute Example** (makes actual OpenRouter call):
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "X-Internal-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "text-completion",
    "payload": {
      "model": "gpt-4",
      "messages": [{"role": "user", "content": "Hello!"}],
      "max_tokens": 50
    },
    "dry_run": false
  }'
```

Response:
```json
{
  "status": "ok",
  "routing": {
    "provider": "openai",
    "model": "gpt-4",
    "endpoint": "/chat/completions"
  },
  "result": {
    "id": "chatcmpl-xxx",
    "choices": [{"message": {"content": "Hello there!"}}]
  },
  "usage": {
    "input_tokens": 8,
    "output_tokens": 5,
    "input_cost": 0.00024,
    "output_cost": 0.0003,
    "subtotal": 0.00054,
    "admin_total": 0.000154,
    "total": 0.000694,
    "estimated": false
  }
}
```

## Supported Job Types

Default routing configuration:
- `text-completion` → OpenAI GPT-4
- `text-generation` → OpenAI GPT-3.5-turbo
- `image-generation` → Stability AI Stable Diffusion XL
- `image-to-video` → Runway Gen-2
- `video-generation` → Runway Gen-2
- `audio-generation` → ElevenLabs Multilingual v2
- `text-to-speech` → ElevenLabs Multilingual v2

## Configuration

### Routing Config

Override with `ROUTING_CONFIG_JSON` or `ROUTING_CONFIG_PATH`:

```json
{
  "text-completion": {
    "provider": "openai",
    "model": "gpt-4",
    "endpoint": "/chat/completions"
  },
  "image-generation": {
    "provider": "stability",
    "model": "stable-diffusion-xl",
    "endpoint": "/images/generations"
  }
}
```

### Pricing Config

Override with `PRICING_CONFIG_JSON` or `PRICING_CONFIG_PATH`:

```json
{
  "gpt-4": {
    "input_cost_per_1k": 0.03,
    "output_cost_per_1k": 0.06
  },
  "stable-diffusion-xl": {
    "per_image": 0.05
  }
}
```

## Security Considerations

### Authentication
- Single API key stored in `INTERNAL_API_KEY` env var
- Uses `hmac.compare_digest()` for timing-attack resistant comparison
- All `/api/*` endpoints require `X-Internal-API-Key` header
- Only `/health` endpoint is unauthenticated

### Logging Sanitization
**NEVER logged**:
- `INTERNAL_API_KEY` env var value
- `OPENROUTER_API_KEY` env var value
- `X-Internal-API-Key` request header
- `Authorization` request header (used for OpenRouter)
- API keys in request/response bodies

All logs are sanitized before writing and before serving via `/api/logs`.

### Fail Fast
Service will not start if required env vars are missing:
- `INTERNAL_API_KEY`
- `OPENROUTER_API_KEY`

### No Shell Execution
- Uses `httpx` for HTTP requests (no subprocess/shell)
- No `shell=True` anywhere in codebase

### Minimal Dependencies
Only essential packages:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `httpx` - Async HTTP client

## Error Handling

All errors return consistent format:
```json
{
  "status": "error",
  "message": "Error description"
}
```

HTTP status codes:
- `200` - Success
- `401` - Missing or invalid API key
- `422` - Validation error (Pydantic)
- `500` - Server error (logged)

## Logging Format

Structured logs in UTC:
```
2026-01-13T10:30:00Z INFO job=abc-123 endpoint=route status=started
2026-01-13T10:30:01Z INFO job=abc-123 status=success job_type=text-completion model=gpt-4
```

## Monitoring

Use `/health` endpoint for liveness/readiness probes:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## License

Internal use only. No public distribution.
