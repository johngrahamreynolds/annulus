# Status: Proposed

## Context

v0.2 runs a **single** `AgentRuntime` loop: retrieve → complete → tools → repeat ([ADR-004](adr-004-retrieval-tools-agent-loop.md)). That suffices for interactive coding assistance. **Engineering and research tasks** often decompose into parallel or sequential subtasks — literature review, code exploration, verification, synthesis — that benefit from **multiple specialized agents** coordinating over shared retrieval and trace infrastructure.

The maintainer's professional work includes a **model-agnostic agent swarm search engine** with **GraphRAG**; Annulus should reuse those patterns (graph-augmented retrieval, merge/rank, delegated workers) while staying workspace-scoped and local-first.

## Decision

Introduce an **orchestrator layer** above `AgentRuntime` in a future phase (target **v0.7**), without breaking the single-agent path used by Continue and CLI today.

**Architecture:**

```text
                    Orchestrator agent
                    (plan · delegate · merge)
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    Research worker    Code worker      Verify worker
    AgentRuntime       AgentRuntime       AgentRuntime
    (scoped retrieval) (tools: rg, git)   (tests, checks)
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
              Shared workspace stores
              FTS · embeddings · graph · traces
```

**Orchestrator responsibilities:**

- Decompose user goal into subtasks (structured plan or tool-like `delegate` calls).
- Spawn **worker runs** — each a bounded `AgentRuntime` invocation with:
  - Assigned **model profile** ([ADR-007](adr-007-remote-compute-profiles.md): laptop vs lab-gpu).
  - Scoped **retrieval filters** (path prefixes, doc types).
  - Scoped **tool allowlist**.
- Merge worker outputs; decide iteration vs final answer.
- Emit **parent/child trace spans** for observability and future UI ([ADR-006](adr-006-multi-client-architecture.md)).

**Shared substrate (build before or with swarms):**

| Layer | Phase | Role in swarm |
|-------|-------|----------------|
| FTS5 chunks | v0.2 ✅ | Worker context seed |
| Embeddings / hybrid | v0.4 | Semantic recall for research agents |
| Graph (symbols, edges) | v0.5 | Multi-hop expansion, dependency questions |
| MCP tools | v0.6 | External APIs, notebooks, databases |

**Single-agent default preserved:**

- `/v1/chat/completions` with `model: local` continues to invoke one `AgentRuntime` unless a config flag or explicit `agents/swarm` profile opts into orchestration.
- Continue and CLI behavior unchanged for v0.x users.

**Local-first swarms:**

- Orchestration logic and indices remain on the user's machine (or sidecar container).
- Workers may call **remote compute profiles** for large models; data stays in workspace-scoped `.annulus/` unless explicitly sent to a tool.

## Consequences

**Positive**

- Natural fit for scientific workflows (hypothesis → search → code → validate).
- Reuses GraphRAG and swarm patterns from related work without coupling codebases.
- Trace tree becomes the audit trail for multi-agent runs.

**Negative**

- Complexity: deadlock, redundant work, cost amplification if workers escalate to frontier freely.
- Requires governance: max worker count, budget caps, human checkpoints for high-risk tools.
- UI ([ADR-006](adr-006-multi-client-architecture.md)) strongly recommended before swarms are mainstream.

## Open questions

- Plan format: orchestrator emits JSON tasks vs native tool_calls (`delegate_task`)?
- Synchronous vs async worker runs (parallel HTTP vs job queue)?
- How much orchestrator state persists across turns vs per-request?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-006-multi-client-architecture.md](adr-006-multi-client-architecture.md)
- [adr-007-remote-compute-profiles.md](adr-007-remote-compute-profiles.md)
- `packages/runtime/src/annulus_runtime/agent.py`
- `packages/trace/`
