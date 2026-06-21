# Status: Accepted

## Context

The first user-facing coding experience should work through **Continue** (and optionally other OpenAI-compatible clients) without building custom IDE UI. Continue expects standard OpenAI chat completion APIs with streaming SSE.

## Decision

Expose an **OpenAI-compatible HTTP API** from the Annulus gateway:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness + Ollama reachability (no auth) |
| `GET /health/ready` | Readiness with auth |
| `GET /v1/models` | Model profile listing for Continue |
| `POST /v1/chat/completions` | Chat with optional streaming |

Authentication uses `Authorization: Bearer <key>` or `X-API-Key`, configured via `ANNULUS_API_KEY`.

MVP behavior is **transparent passthrough** to Ollama after profile resolution. Agent loop, retrieval, and tool execution will be added inside this endpoint in later phases without breaking the client contract.

Every chat request writes a **SQLite trace span** (`chat.completions`) with model, stream flag, and trace ID returned via `X-Annulus-Trace-Id`.

## Consequences

**Positive**

- Continue works with minimal config
- Same API supports CLI, future web UI, and cloud clients
- Trace store enables eval and self-improvement loops later

**Negative**

- OpenAI API surface is a compatibility constraint; exotic provider features need adapter layers
- Passthrough alone does not yet differentiate Annulus from a proxy (retrieval/tools come next)

## References

- `apps/gateway/src/annulus_gateway/routes/chat.py`
- `docs/continue-config.example.yaml`
