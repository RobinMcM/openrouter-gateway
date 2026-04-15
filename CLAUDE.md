# CLAUDE.md — openrouter-gateway

## Service Identity
Internal microservice for OpenRouter model routing, cost estimation, and execution.
- **Language**: Python 3.11
- **Framework**: FastAPI + Pydantic
- **HTTP Client**: httpx (async)
- **Deployed at**: `https://models.rapidmvp.io` (DigitalOcean Droplet)
- **Local dev**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Structure
```
app/
  main.py          ← entry point, route registration
  routes/          ← endpoint handlers
  models/          ← Pydantic schemas
  services/        ← business logic, OpenRouter client
  config.py        ← env var loading
scripts/
  run_canary.py    ← gated canary test runner
```

## Rules — Read Before Every Task

### Scope
- Only modify the file(s) explicitly named in the request
- Do not refactor, rename, or reorganise files not mentioned
- Do not add new dependencies without explicit confirmation
- Do not modify `requirements.txt` unless asked

### Git
- Do NOT run any git commands
- Do NOT stage, commit, or push changes
- Developer handles all git operations

### Running the Service
- Do NOT attempt to start, stop, or restart the service
- Do NOT run uvicorn or any server process
- Do NOT run docker commands
- Do NOT run canary scripts unless explicitly asked

### Testing
- Do NOT run pytest or any test commands automatically
- If tests are needed, suggest the command and wait for confirmation

### Security — Critical
- NEVER log, print, or expose `INTERNAL_API_KEY` or `OPENROUTER_API_KEY`
- All new endpoints under `/api/*` MUST use `hmac.compare_digest` authentication
- Only `/health` is unauthenticated — do not change this
- Maintain secret sanitisation in all logging

### Environment Variables
- Required: `INTERNAL_API_KEY`, `OPENROUTER_API_KEY`
- Optional: `OPENROUTER_BASE_URL`, `ADMIN_MARKUP_PERCENT`, `ADMIN_FIXED_FEE`
- `ROUTING_CONFIG_JSON` / `ROUTING_CONFIG_PATH` for routing overrides
- `PRICING_CONFIG_JSON` / `PRICING_CONFIG_PATH` for pricing overrides
- Never hardcode values — always use env vars

## Current Endpoints
- `GET /health` — unauthenticated
- `GET /api/instructions` — authenticated
- `GET /api/logs` — authenticated
- `POST /api/route` — routing decision + cost estimate (no OpenRouter call)
- `POST /api/execute` — execute or dry-run OpenRouter call

## Supported Job Types
text-completion, text-generation, image-generation, image-to-video,
video-generation, audio-generation, text-to-speech

## Error Response Format — Always Maintain
```json
{"status": "error", "message": "description"}
```

## Phase 1 Build Target
Adding SSE streaming endpoint: `POST /api/execute/stream`
- Must maintain same auth pattern as `/api/execute`
- Must accept optional `user_ref` field for logging
- Must not break existing `/api/execute` endpoint

## If Uncertain
Ask before proceeding. Do not infer intent and act.
