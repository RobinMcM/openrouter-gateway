# CLAUDE.md — openrouter-gateway

## Service Identity
Stateless AI execution gateway. Passes requests to OpenRouter (text) or FAL.ai
(media) and returns results with cost information.

**The gateway does not track billing or attribute costs to users.**
Cost tracking is the responsibility of the calling service (MovieShakerV2 engine).
The gateway uses Valkey only for in-flight async job state (FAL media jobs) —
this is transient state, not persistent billing data.

- **Language**: Python 3.11
- **Framework**: FastAPI + Pydantic
- **HTTP Client**: httpx (async)
- **Providers**: OpenRouter (text), FAL.ai (image/video/audio)
- **Job State**: Valkey (async FAL jobs only — transient)
- **Auth**: `X-Internal-API-Key` header via `hmac.compare_digest`
- **CORS**: Handled by Nginx — not in FastAPI
- **Deployed at**: `https://models.rapidmvp.io` (DigitalOcean Droplet)
- **Local dev**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Structure
```
app/
  main.py                    ← entry point, all route registrations
  auth.py                    ← API key verification (hmac.compare_digest)
  config.py                  ← routing + pricing config loading
  config_manager.py          ← runtime OpenRouter key management
  logger.py                  ← structured logging with secret sanitisation
  models_data.py             ← OpenRouter model list
  movieshaker_models_data.py ← MovieShaker-specific model catalog
  openrouter_models_showcase.py ← model showcase data
  schemas.py                 ← all Pydantic request/response models
  providers/
    openrouter_client.py     ← OpenRouter API client
    fal_client.py            ← FAL.ai API client (sync + queue)
  routing/
    media_routing.py         ← FAL media type → model routing
  pricing/
    media_pricing.py         ← FAL cost estimation and extraction
  job_store/
    valkey_store.py          ← transient async job state (FAL only)
  services/
    model_registry.py        ← dynamic model list from FAL
  transforms/
    media_transformer.py     ← generic request → provider-specific format
nginx/
  conf.d/
    models.rapidmvp.io.conf  ← HTTPS + CORS config
scripts/
  run_canary.py              ← gated health + smoke test runner
```

## Rules — Read Before Every Task

### Scope
- Only modify the file(s) explicitly named in the request
- Do not modify `nginx/` config without explicit confirmation
- Do not modify `auth.py` without explicit confirmation
- Do not modify `schemas.py` without reviewing all usages first

### Git
- Do NOT run any git commands
- Developer handles all git operations

### Running the Service
- Do NOT start, stop, or restart the service
- Do NOT run docker commands
- Do NOT run canary scripts unless explicitly asked
- If a restart is needed, suggest the command and wait

### Testing
- Do NOT run tests automatically
- Canary runner: `python3 scripts/run_canary.py`
- Requires `.env` with `GATEWAY_BASE_URL`, `GATEWAY_INTERNAL_API_KEY`

### Security — Critical
- NEVER log or expose `INTERNAL_API_KEY`, `OPENROUTER_API_KEY`, or `FAL_KEY`
- All `/api/*` endpoints require `X-Internal-API-Key`
- `/api/logs` requires `ADMIN_API_KEY` if set, otherwise `INTERNAL_API_KEY`
- Only `/health` is unauthenticated

## API Endpoints

### Unauthenticated
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |

### Authenticated (`X-Internal-API-Key`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/instructions` | Full API documentation |
| GET | `/api/logs` | Sanitised logs (admin only) |
| POST | `/api/route` | Cost estimate only — no provider call |
| POST | `/api/execute` | OpenRouter text OR FAL media (discriminated by `provider` field) |
| POST | `/api/media/execute` | Generic media execute (new contract) |
| GET | `/api/models` | OpenRouter model list |
| GET | `/api/media/models` | FAL media model list (filterable by `media_type`) |
| GET | `/api/models/showcase` | MovieShaker model showcase |
| GET | `/api/status/{job_id}` | FAL async job status |
| GET | `/api/result/{job_id}` | FAL async job result |
| GET | `/api/results/{job_id}` | Alias for `/api/result/{job_id}` |

### Admin only
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/openrouter-key/status` | OpenRouter key config status |
| POST | `/api/config/openrouter-key` | Update OpenRouter key at runtime |
| POST | `/api/config/openrouter-key/test` | Test an OpenRouter key |

## Provider Contracts

### OpenRouter (text)
```
POST /api/execute
{
  "provider": "openrouter",
  "job_type": "text-completion",
  "payload": { "model": "...", "messages": [...] },
  "dry_run": false
}
→ { status, routing, result, usage }
```
Synchronous. Returns immediately with result and cost.

### FAL.ai (media — legacy)
```
POST /api/execute
{
  "provider": "fal",
  "media_type": "image-generation",
  "model": "fal-ai/flux/schnell",
  "payload": { "prompt": "..." },
  "dry_run": false
}
→ { ok, job_id, job_status, status_url, estimate }
```
Asynchronous. Poll `/api/status/{job_id}` until `job_status` is `completed` or `failed`.

### FAL.ai (media — generic contract)
```
POST /api/media/execute
{
  "provider": "fal",
  "query_type": "image-video",
  "model": "fal-ai/veo3/image-to-video",
  "source_image": "https://...",
  "options": { "duration": "6s" },
  "dry_run": false
}
→ GenericExecuteResponse (normalised fields, stage history, cost)
```

## Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `INTERNAL_API_KEY` | ✅ | Auth key for all `/api/*` endpoints |
| `OPENROUTER_API_KEY` | ✅ | OpenRouter API key |
| `FAL_KEY` | ✅ | FAL.ai API key |
| `ADMIN_API_KEY` | | Admin-only endpoints (logs, config) |
| `OPENROUTER_BASE_URL` | | Default: `https://openrouter.ai/api/v1` |
| `FAL_SYNC_BASE` | | Default: `https://fal.run` |
| `FAL_QUEUE_BASE` | | Default: `https://queue.fal.run` |
| `ADMIN_MARKUP_PERCENT` | | Default: `0.10` |
| `ADMIN_FIXED_FEE` | | Default: `0.001` |
| `ROUTING_CONFIG_JSON` | | Override routing config inline |
| `ROUTING_CONFIG_PATH` | | Override routing config from file |
| `PRICING_CONFIG_JSON` | | Override pricing config inline |
| `PRICING_CONFIG_PATH` | | Override pricing config from file |

## Cost / Billing Architecture
The gateway returns cost information per request in the `usage` field.
**It does not accumulate or track costs across requests.**
The calling service (MovieShakerV2 engine) is responsible for:
- Attributing costs to users
- Accumulating per-user totals
- Enforcing credit limits

## If Uncertain
Ask before proceeding. Do not infer intent and act.
One task at a time. Wait for confirmation before the next step.
