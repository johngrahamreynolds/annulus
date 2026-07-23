# Annulus vision and roadmap

Local-first, model-agnostic agentic platform for **engineering and scientific research**. v0.x proves the engine via IDE clients (Continue); later iterations add hybrid retrieval, graphs, swarms, remote compute, and a dedicated UI.

## Architectural layers

```text
┌─────────────────────────────────────────────────────────┐
│  Experience layer (pluggable clients)                    │
│  Continue · Annulus UI · CLI · notebooks · CI / bots     │
└───────────────────────────┬─────────────────────────────┘
                            │  OpenAI-compatible API (+ future agent/trace APIs)
┌───────────────────────────▼─────────────────────────────┐
│  Annulus engine (stable core)                            │
│  AgentRuntime · ModelRouter · Retrieval · Tools · Trace  │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  Workspace-scoped stores                                 │
│  FTS index · embeddings · graph · traces (.annulus/)     │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  Compute tier (configurable profiles)                    │
│  laptop Ollama · remote GPU server · frontier APIs       │
└─────────────────────────────────────────────────────────┘
```

## Principles

1. **Sidecar, not embed** — Annulus is an engine; target repos stay clean. Workspace data lives in `.annulus/` on the mounted project.
2. **One client contract** — OpenAI-compatible `/v1` for chat; extend with trace/index APIs without breaking existing clients ([ADR-003](adr-003-openai-compatible-gateway.md)).
3. **Local-first, escalate deliberately** — Prefer on-prem and self-hosted inference; frontier and remote lab GPUs are configured tiers, not hard dependencies ([ADR-005](adr-005-frontier-escalation.md), [ADR-007](adr-007-remote-compute-profiles.md)).
4. **Retrieval before generation** — Lexical search first (v0.2); embeddings and graphs layered in as recall and structure demands grow ([ADR-004](adr-004-retrieval-tools-agent-loop.md)).
5. **Eval-driven iteration** — Dogfood on real repos; traces and prompt matrices drive the backlog.

## North star

An **agentic engineering and research platform**: grounded in the user's repos, notes, and data; cheap by default on local hardware; able to delegate to lab GPU servers or frontier APIs; eventually coordinating **agent swarms** over a **GraphRAG** substrate — with a **native UI** for chat, context, graphs, and run timelines.

## Phase roadmap

| Phase | Focus | Primary client |
|-------|--------|----------------|
| **v0.2** ✅ | FTS5 retrieval, tool loop, tracing, frontier escalation, eval devcontainer | Continue / CLI |
| **v0.3** ✅ | **git-aware index watch**, **trace CLI**, **git tools**, eval runbook, **0.3.0** tag. Shipped: streaming tool loop, Gemma profiles (ADR-013), Continue tool prompt, reasoning Thought UI, Windows eval, ChatDescriber passthrough | Continue / CLI |
| **v0.4** | **Local SWE assistant** ([ADR-015](adr-015-local-swe-assistant-v04.md)): hybrid FTS + embeddings (ADR-009), incremental re-embed, **propose_edit** + Continue edit/apply, team runbook. `propose_edit`'s apply mode is gated by [ADR-019](adr-019-permission-capability-model.md)/[ADR-021](adr-021-plan-before-act-protocol.md) | Continue / CLI |
| **v0.5** | GraphRAG-lite (symbols, edges, multi-hop expand) | CLI + trace inspection |
| **v0.6** | MCP tools, remote compute profiles (lab GPU / vLLM) | Clients unchanged |
| **v0.7** | Orchestrator + worker agent swarms | IDE optional |
| **v1.0** | Annulus UI (chat, side panes, graph/trace/swarm views) | Dedicated UI + API |

## Related ADRs

See [`adr-template.md`](adr-template.md) for the section structure new ADRs follow.

| ADR | Topic | Status |
|-----|--------|--------|
| [001](adr-001-monorepo-uv.md) | Monorepo and uv workspace | Accepted |
| [002](adr-002-host-ollama-docker-apps.md) | Host Ollama, Docker/devcontainer | Accepted |
| [003](adr-003-openai-compatible-gateway.md) | OpenAI-compatible gateway | Accepted |
| [004](adr-004-retrieval-tools-agent-loop.md) | Retrieval, tools, agent loop | Accepted |
| [005](adr-005-frontier-escalation.md) | Frontier escalation | Accepted |
| [006](adr-006-multi-client-architecture.md) | Multi-client / UI direction | Proposed |
| [007](adr-007-remote-compute-profiles.md) | Remote and lab GPU inference | Proposed |
| [008](adr-008-agent-swarm-orchestration.md) | Swarm orchestration | Proposed |
| [009](adr-009-hybrid-retrieval-embeddings.md) | Hybrid FTS + embeddings | Proposed |
| [010](adr-010-graphrag-lite.md) | GraphRAG-lite | Proposed |
| [011](adr-011-governed-self-improvement.md) | Governed self-improvement (open-ended) | Proposed |
| [012](adr-012-target-native-sidecar-deployment.md) | Target-native sidecar / end-user deployment | Proposed |
| [013](adr-013-model-tool-compatibility.md) | Model tool compatibility matrix | Proposed |
| [014](adr-014-incremental-index-watch.md) | Git-aware incremental index watch | Accepted |
| [015](adr-015-local-swe-assistant-v04.md) | Local SWE assistant (v0.4 edit + hybrid retrieval) | Proposed |
| [016](adr-016-typescript-client-layer.md) | TypeScript client-layer strategy | Proposed |
| [017](adr-017-skill-primitive.md) | Skill primitive (Tool↔Skill↔Agent boundary) | Proposed |
| [018](adr-018-agent-identity-configuration.md) | Agent identity & configuration | Proposed |
| [019](adr-019-permission-capability-model.md) | Permission & capability authorization model | Proposed |
| [020](adr-020-data-egress-compliance-policy.md) | Data-egress & compliance policy (ITAR/ZDR) | Proposed |
| [021](adr-021-plan-before-act-protocol.md) | Plan-before-act interaction protocol | Proposed |
| [022](adr-022-per-project-agent-policy.md) | Per-project / per-agent policy (`.annulus/config.yaml`) | Proposed |
| [023](adr-023-provenance-evaluation-data-model.md) | Provenance & evaluation data model | Proposed |
| [024](adr-024-scientific-workload-primitives.md) | Scientific workload primitives | Proposed |

## Architecture reviews

Point-in-time gap analyses vs this vision (historical snapshots, not live status): [reviews/](reviews/README.md).

## Eval signals → next work

| Symptom in eval | Likely next layer |
|-----------------|-------------------|
| Wrong file, right keywords | v0.4 embeddings / hybrid retrieval |
| Cross-module / dependency questions | v0.5 graph expansion |
| Model too small or slow | v0.6 remote `lab-gpu` profile |
| Multi-step research workflows | v0.7 swarm orchestrator |
| Hard to inspect hits and tool spans while working | v1 Annulus UI |
| Tool returns too few matches (rg / top_k / model summarization) | Tool defaults, retrieval `top_k`, response prompting; see work-eval notes |
| Search-only feels like Ctrl+F; need edit/write/diff for SWE MVP | v0.3 git tools (shipped); v0.4 propose_edit + Continue edit/apply ([ADR-015](adr-015-local-swe-assistant-v04.md)) |
| Engine in Annulus window vs code in target window | Target-native sidecar / index watch (v0.3 deployment) |
| Model cites "supplied context" awkwardly | System prompt / injection format tuning |
| Model emits tool JSON in content, not `tool_calls` | [ADR-013](adr-013-model-tool-compatibility.md) — probe, profile flags, optional fallback |
| Full reindex too slow on large repos | [ADR-014](adr-014-incremental-index-watch.md) — git-aware incremental watch |
| Agent executes a risky/irreversible action with no chance to review | [ADR-021](adr-021-plan-before-act-protocol.md) — plan-before-act |
| Workspace content reaches a frontier API with no policy check | [ADR-020](adr-020-data-egress-compliance-policy.md) — egress policy |
| Same domain workflow re-implemented by hand every time | [ADR-017](adr-017-skill-primitive.md) — skill primitive |
| Trace tree is flat; can't see multi-agent nesting | [ADR-023](adr-023-provenance-evaluation-data-model.md) — `parent_span_id` wiring (#40) |
