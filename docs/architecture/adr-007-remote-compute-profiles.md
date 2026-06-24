# Status: Proposed

## Context

Annulus is **local-first**: Ollama on the host, workspace data on disk, no required cloud API. In practice, users often have access to **more capable hardware elsewhere** — e.g. a lab machine with an Nvidia RTX PRO 6000 running vLLM, Ollama, or LiteLLM — that is still *their* infrastructure, not a public frontier API.

Today:

- **Local** profiles use `provider: ollama` via `OLLAMA_HOST` ([ADR-002](adr-002-host-ollama-docker-apps.md)).
- **Frontier** profiles use `provider: openai` with `OPENAI_BASE_URL` and `OPENAI_API_KEY` ([ADR-005](adr-005-frontier-escalation.md)).

There is no first-class way to express "run this agent on the GPU server at `10.x.x.x`" while keeping orchestration and data local on the laptop.

## Decision

Extend **`config/models.yaml` profiles** to support **remote OpenAI-compatible and Ollama endpoints** as explicit compute tiers, not ad hoc frontier fallbacks.

**Profile tiers (conceptual):**

```yaml
profiles:
  local:
    provider: ollama
    model: llama3.1:8b
    # default: OLLAMA_HOST / host.docker.internal

  lab-gpu:
    provider: openai          # OpenAI-compatible HTTP API
    model: qwen2.5-72b-instruct
    apiBase: http://10.0.1.50:8000/v1
    apiKey: ${LAB_GPU_API_KEY}   # or shared secret on internal network
    supports_tools: true
    description: vLLM or LiteLLM on lab RTX box

  frontier:
    provider: openai
    model: gpt-4o-mini
    apiBase: https://litellm.example/v1
    supports_tools: true
```

**Routing policy:**

- Clients select profile via `model` field (`local`, `lab-gpu`, `frontier`) — unchanged OpenAI contract.
- **Escalation ladder** may be extended from binary local→frontier to **tiered**: `local` → `lab-gpu` → `frontier`, configured in `models.escalation` (future).
- **Swarm workers** ([ADR-008](adr-008-agent-swarm-orchestration.md)) may bind different profiles per role (orchestrator on laptop, workers on `lab-gpu`).

**Implementation notes (when built):**

- `ModelRouter` already supports per-profile `apiBase`; remote Ollama is `provider: ollama` with explicit `apiBase: http://remote:11434`.
- Document TLS, API keys, and network allowlists for remote endpoints.
- Health check should report reachability per profile (`lab-gpu: ok | unavailable`).

**Security:**

- Remote inference endpoints must require authentication (API key or mTLS).
- Annulus gateway API key (`ANNULUS_API_KEY`) protects the engine; remote profile keys protect compute backends — separate concerns.

## Consequences

**Positive**

- "Local" means *user-controlled*, not *same physical machine*.
- Cost-efficient default on laptop; heavy models on lab hardware without cloud dependency.
- Aligns with work environments where a shared GPU server is available on the LAN.

**Negative**

- Latency and network failures on remote profiles; escalation and health reporting must handle unreachable lab hosts.
- Operational burden: users maintain remote inference stack (vLLM/Ollama/LiteLLM versions, models pulled).

## References

- [vision.md](vision.md)
- [adr-002-host-ollama-docker-apps.md](adr-002-host-ollama-docker-apps.md)
- [adr-005-frontier-escalation.md](adr-005-frontier-escalation.md)
- `config/models.yaml`
- `packages/router/src/annulus_router/router.py`
