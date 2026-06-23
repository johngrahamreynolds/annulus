# Status: Accepted

## Context

Local models on constrained hardware will sometimes fail or return low-quality empty responses. Frontier APIs add cost but improve reliability for hard tasks.

## Decision

Implement escalation in `packages/router`:

- `ModelRouter.complete()` tries the resolved local profile first
- On local **error** or **empty content**, retry once with the configured `frontier` profile (OpenAI-compatible)
- Controlled by `router.escalation_enabled`, `models.escalation.*`, `OPENAI_API_KEY`, and `OPENAI_BASE_URL`
- The `frontier` profile uses `provider: openai` (OpenAI-compatible HTTP API). Point `OPENAI_BASE_URL` at OpenAI, LiteLLM, or another compatible gateway; set `model` in `config/models.yaml` to the upstream model or LiteLLM alias

Escalation is recorded in trace spans and returned via `annulus.escalated` in non-streaming responses.

## Consequences

**Positive**

- Graceful degradation path without client changes
- Explicit health reporting (`frontier: configured | missing_api_key`)

**Negative**

- Unexpected API cost if escalation triggers often — tune local models and eval traces
- Only OpenAI-compatible frontier provider implemented

## References

- `packages/router/src/annulus_router/escalation.py`
- `packages/router/src/annulus_router/router.py`
- `config/models.yaml`
