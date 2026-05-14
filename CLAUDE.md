# CLAUDE.md — openrouter-gateway

## Service Identity
Stateless AI execution gateway. Passes requests to OpenRouter (text, image,
video) and returns results with cost information.

**The gateway does not track billing or attribute costs to users.**
Cost tracking is the responsibility of the calling service (MovieShakerV2 engine).

- **Language**: Python 3.11
- **Framework**: FastAPI + Pydantic
- **HTTP Client**: httpx (sync for image/video, async for text)
- **Providers**: OpenRouter only (text, synchronous image, synchronous video)
- **Auth**: `X-Internal-API-Key` header via `hmac.compare_digest`
- **CORS**: Handled by Nginx — not in FastAPI
- **Deployed at**: `https://models.rapidmvp.io` (DigitalOcean Droplet)
- **Local dev**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Structure
```
app/
  main.py                       ← entry point, all route registrations
  auth.py                       ← API key verification (hmac.compare_digest)
  config.py                     ← routing + pricing config loading
  config_manager.py             ← runtime OpenRouter key management
  logger.py                     ← structured logging with secret sanitisation
  image_models.py               ← OpenRouter image model catalogue
  video_models.py               ← OpenRouter video model catalogue
  models_data.py                ← OpenRouter text model list
  movieshaker_models_data.py    ← MovieShaker-specific model catalog
  openrouter_models_showcase.py ← model showcase data
  schemas.py                    ← all Pydantic request/response models
  providers/
    openrouter_client.py        ← OpenRouter text API client
    openrouter_image_client.py  ← OpenRouter synchronous image client
    openrouter_video_client.py  ← OpenRouter synchronous video client
  tasks/
    task_registry.py            ← task catalogue (task name → ranked models)
    task_router.py              ← resolve_task() — picks best available model
nginx/
  conf.d/
    models.rapidmvp.io.conf     ← HTTPS + CORS config
scripts/
  run_canary.py                 ← gated health + smoke test runner
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
- NEVER log or expose `INTERNAL_API_KEY` or `OPENROUTER_API_KEY`
- All `/api/*` endpoints require `X-Internal-API-Key`
- `/api/logs` requires `ADMIN_API_KEY` if set, otherwise `INTERNAL_API_KEY`
- Only `/health` is unauthenticated

## API Endpoints

### Unauthenticated
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/models` | HTML: OpenRouter model showcase page |
| GET | `/models-showcase` | HTML: MovieShaker AI tools showcase page |
| GET | `/config` | HTML: Owner config page |

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
| POST | `/api/image/generate` | OpenRouter synchronous image generation (base64) |
| GET | `/api/video/models` | OpenRouter video model catalogue |
| POST | `/api/video/generate` | OpenRouter synchronous video generation (URL) |
| GET | `/api/tasks` | Task catalogue with resolved models |
| POST | `/api/task/execute` | Resolve task → model → dispatch |
| POST | `/api/classify` | Classify user message to MovieShaker agent |

### Admin only
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/openrouter-key/status` | OpenRouter key config status |
| POST | `/api/config/openrouter-key` | Update OpenRouter key at runtime |
| POST | `/api/config/test-openrouter-key` | Test an OpenRouter key |

## Provider Contracts

### OpenRouter text
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

### OpenRouter image
```
POST /api/image/generate
{
  "model_key": "nano-banana",
  "prompt": "...",
  "aspect_ratio": "16:9",
  "dry_run": false
}
→ { ok, image_b64, content_type, model, model_key, dry_run }
```

### OpenRouter video
```
POST /api/video/generate
{
  "model_key": "kling-v3-pro",
  "prompt": "...",
  "source_image": "https://...",   # optional (image-to-video)
  "duration": 5,
  "aspect_ratio": "16:9",
  "dry_run": false
}
→ { ok, video_url, content_type, model, model_key, dry_run }
```

### Task execute
```
POST /api/task/execute
{
  "task": "generate-shot",
  "source": "https://...",         # optional source image
  "prompt": "...",
  "options": { "duration": 5 },
  "dry_run": false
}
→ { ok, task, resolved_model, endpoint, dry_run, result }
```
Task registry: `app/tasks/task_registry.py`
Resolver: `app/tasks/task_router.py`

## Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `INTERNAL_API_KEY` | ✅ | Auth key for all `/api/*` endpoints |
| `OPENROUTER_API_KEY` | ✅ | OpenRouter API key |
| `ADMIN_API_KEY` | | Admin-only endpoints (logs, config) |
| `OPENROUTER_BASE_URL` | | Default: `https://openrouter.ai/api/v1` |
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
