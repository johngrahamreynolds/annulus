# Status: Proposed

## Context

Annulus aims to grow in capability over time — not only through manual engineering of each release, but through **governed learning** from use: better retrieval, skills, routing, and (eventually) workspace memory. This aligns with patterns seen in deep agent products (persistent project memory, improving agent configs, long-horizon coding agents) while staying **local-first** and **workspace-scoped**.

This ADR intentionally stays **open-ended**. Implementation details will be revisited as v0.3–v1.0 land and real evals (including work-repo dogfooding) reveal what improvement loops are worth automating.

## Intent (core tenet)

The system should become **more useful the longer it supports a workspace**, without silent or unbounded self-modification.

**Domain (physics, mathematics, software engineering, etc.)** is not a separate product mode. It emerges from:

- What is indexed in the workspace
- User/project **rules** and **skills** under `.annulus/`
- Tools and MCP servers configured for that domain
- Graph and memory content (future)

The **engine remains domain-agnostic**; discipline-specific behavior is layered on top.

## Improvement loops (conceptual — order and shape TBD)

| Loop | Rough idea | Depends on | Timing (indicative) |
|------|------------|------------|---------------------|
| **A — Retrieval & index** | Eval misses → proposed chunk/index/graph tweaks → human approves → reindex | Hybrid retrieval, graph, eval CLI | Late v0.x |
| **B — Skills & routing** | Repeated successful traces → proposed skill or profile routing | Trace API, swarms optional | v1.x |
| **C — Memory** | Summarized episodic/semantic memory across sessions | Dedicated memory store, UI to inspect/edit | v1.1+ |
| **D — Meta-agent** | Orchestrator proposes config/rule/tool changes | UI diff + governance, memory | Post–v1.0; design TBD |

All loops should default to **propose, don't apply**. Traces and eval prompts are inputs; humans (or explicit policy) approve mutations.

## Foundations to preserve while building v0.3–v1.0

- Traces are **observability**, not chat memory ([ADR-004](adr-004-retrieval-tools-agent-loop.md)).
- Persistent memory, when added, lives under `.annulus/` as a **first-class store**, not in `traces.db`.
- Behavior changes go through **config and workspace artifacts** (YAML, rules, skills) so they can be diffed, reviewed, and reverted.
- **Eval-driven regression** (work-repo and Annulus-repo prompt matrices) gates any automated improvement.
- **Model tool compatibility** evolves via probes and traces ([ADR-013](adr-013-model-tool-compatibility.md)) — feeds Loop B, not hard-coded per release.

## Deployment paths

| Audience | Path | Doc |
|----------|------|-----|
| Contributors (now) | Annulus eval devcontainer + Continue in target repo | `.devcontainer/eval/`, [ADR-012](adr-012-target-native-sidecar-deployment.md) |
| End users (later) | Target-native sidecar; minimal config pointing at repo | [ADR-012](adr-012-target-native-sidecar-deployment.md) |

## Non-goals (for now)

- Fully autonomous self-modification of engine code or gateway logic without review.
- Hard-coded discipline packs in core (e.g. "physics mode" in `AgentRuntime`).
- Using frontier APIs to "learn" without local audit trail.

## Open questions (to reevaluate during development)

- What is stored in memory vs re-retrieved from index each turn?
- Which improvement loops justify automation vs assistant-generated suggestions only?
- How do swarms ([ADR-008](adr-008-agent-swarm-orchestration.md)) participate in improvement — orchestrator-only or workers too?
- Relationship to external brain products (import/export memory graph)?

## References

- [vision.md](vision.md)
- [adr-006-multi-client-architecture.md](adr-006-multi-client-architecture.md)
- [adr-008-agent-swarm-orchestration.md](adr-008-agent-swarm-orchestration.md)
- [adr-013-model-tool-compatibility.md](adr-013-model-tool-compatibility.md)
