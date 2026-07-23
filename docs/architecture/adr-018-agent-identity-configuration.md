# Status: Proposed
**Date:** 2026-07-22

## Context

There is exactly one `AgentRuntime` (`packages/runtime/src/annulus_runtime/agent.py:66`),
constructed once at gateway startup (`apps/gateway/deps.py`) with `settings, router,
retriever, tools, trace_store`. Neither `run()` nor `stream_run()` (`agent.py:81-89,
120-127`) accepts anything resembling an agent identity — the only per-request
knob is `profile_name`, which selects a *model routing profile*
([ADR-013](adr-013-model-tool-compatibility.md)), not an agent role, prompt, or
permission set.

[ADR-008](adr-008-agent-swarm-orchestration.md) already describes an orchestrator
delegating to "research worker / code worker / verify worker," each an `AgentRuntime`
invocation with "assigned model profile, scoped retrieval filters, scoped tool
allowlist" — but never defines what an individual agent *is* as a config object. The
swarm ADR floats above a missing primitive. Pillar 1 of the review also names this
gap directly: the runtime owns tools, context, and routing, but not "agents
(plural)."

`ANNULUS_API_KEY` (`config.py:94`) and `ANNULUS_WORKSPACE_ROOT` (`config.py:100`) are
process-wide; there is no way today to say "this conversation should run as the
planner role with a narrower retrieval scope and no write tools" without hand-editing
the system prompt on the client side, which re-implements exactly the logic
[ADR-006](adr-006-multi-client-architecture.md) says clients must not own.

## Decision

Define an `AgentConfig` object: `name`, `role` (free-text label for prompt/selection
purposes), a `system_prompt` fragment (appended to, not replacing, the base tool
system prompt from `config/default.yaml`'s `agent.tool_system_prompt`), a bound
`model_profile` (references `config/models.yaml`), a `retrieval_scope` (path
prefixes / doc-type filters passed to `Retriever.search()`), a `skills: list[str]`
([ADR-017](adr-017-skill-primitive.md)), and a `capabilities` tool allowlist
([ADR-019](adr-019-permission-capability-model.md)). A `memory_scope` field is
reserved (declared in the schema, unimplemented) — actual memory storage is
[ADR-011](adr-011-governed-self-improvement.md) Loop C (v1.1+); this ADR only makes
sure the config object won't need a breaking schema change when that lands.

**Storage:** `.annulus/agents/*.yaml`, workspace-scoped like
[ADR-017](adr-017-skill-primitive.md)'s skills, loaded by the same mechanism (or a
sibling loader in the same package).

**Runtime integration:** `AgentRuntime.__init__` / `run()` / `stream_run()` gain an
optional `agent_config: AgentConfig | None` parameter. When `None` (every call site
today — Continue, CLI `chat`, CLI `health`-adjacent paths), behavior is byte-for-byte
identical to the current implicit single-runtime behavior: `AgentConfig.default()` is
exactly today's hardcoded defaults (`profile_name` from request, full tool set, no
retrieval scope, no skills). This is the load-bearing compatibility guarantee of this
ADR — existing clients see zero behavior change.

**Relationship to skills ([ADR-017](adr-017-skill-primitive.md)):** an agent may load
skills; a skill cannot load an agent. An agent's `capabilities` allowlist is the outer
bound — a loaded skill's tool allowlist can only narrow it, never widen it (same rule
[ADR-019](adr-019-permission-capability-model.md) states for capability resolution
generally).

**Non-goals:** no multi-tenant/multi-user identity (this is agent-as-a-configured-role,
not user authentication); no agent-to-agent messaging protocol (that's
[ADR-008](adr-008-agent-swarm-orchestration.md)'s orchestration layer, built on top of
this primitive, not defined here); no dynamic runtime mutation of an agent's own
config (governed self-modification is explicitly deferred to
[ADR-011](adr-011-governed-self-improvement.md) Loop D).

## Consequences

**Positive**

- Gives [ADR-008](adr-008-agent-swarm-orchestration.md) swarm orchestration a real
  foundation instead of an assumed one — "spawn a worker run" becomes "instantiate
  `AgentRuntime` with this `AgentConfig`," a mechanical operation.
- Zero behavior change for existing single-agent callers (Continue, CLI) — the
  default-config path is exactly today's runtime.
- Gives [ADR-017](adr-017-skill-primitive.md) skills a natural owner (an agent loads
  skills) instead of skills needing their own top-level selection mechanism.

**Negative**

- Another workspace-scoped YAML surface (`.annulus/agents/`) alongside skills
  (`.annulus/skills/`) and eventual per-project policy
  ([ADR-022](adr-022-per-project-agent-policy.md)) — total `.annulus/` surface area
  keeps growing and needs a documented map, not three independently-evolving schemas.
- `AgentConfig.default()` must be kept in exact lockstep with `AgentRuntime`'s actual
  hardcoded defaults as the runtime evolves, or the "zero behavior change" guarantee
  quietly breaks.
- Retrieval-scope filtering requires `Retriever.search()` to accept scope parameters
  it doesn't have today — a real (if small) `packages/retrieval` change, not purely
  additive.

## Open questions

- Does `role` drive automatic prompt/behavior selection, or is it purely a label for
  humans/orchestrators to read — overlaps [ADR-017](adr-017-skill-primitive.md)'s
  open question about automatic vs. explicit skill selection.
- Can a single HTTP request specify `agent_config` inline (e.g. a new field on the
  chat completion request), or is it resolved server-side only from a name reference
  — affects how much of this is visible over `/v1/chat/completions` vs. internal-only
  until [ADR-008](adr-008-agent-swarm-orchestration.md) needs it exposed.
- Should `AgentConfig` validation happen at gateway startup (fail fast on malformed
  `.annulus/agents/*.yaml`) or lazily per-request?
- How does `memory_scope` get validated as "reserved but unimplemented" without
  either over-specifying a schema that memory work later has to break, or
  under-specifying it so badly it's not actually reserving anything?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-006-multi-client-architecture.md](adr-006-multi-client-architecture.md)
- [adr-008-agent-swarm-orchestration.md](adr-008-agent-swarm-orchestration.md)
- [adr-011-governed-self-improvement.md](adr-011-governed-self-improvement.md)
- [adr-013-model-tool-compatibility.md](adr-013-model-tool-compatibility.md)
- [adr-017-skill-primitive.md](adr-017-skill-primitive.md)
- [adr-019-permission-capability-model.md](adr-019-permission-capability-model.md)
- `packages/runtime/src/annulus_runtime/agent.py`
- `packages/core/src/annulus_core/config.py`
