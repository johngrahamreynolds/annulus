# Status: Proposed

## Context

v0.2 validates Annulus through **Continue** and the **CLI** — sufficient for proving retrieval, tools, and routing on a software-engineering task. The long-term product is not IDE-bound: researchers and engineers need a dedicated surface for chat, retrieved context, graphs, diffs, and run timelines (similar in spirit to Cursor's Agents window with side panels).

The gateway and `AgentRuntime` must remain **client-agnostic** so IDE integration stays a first-class but not exclusive path.

## Decision

Treat all user-facing surfaces as **clients of the Annulus engine**:

| Client | Role | v0.x |
|--------|------|------|
| **Continue / VS Code** | MVP dogfood; OpenAI-compatible chat | Primary |
| **CLI** (`annulus chat`, `health`, `index`) | Scripting, eval, `--no-stream` agent loop | Primary |
| **Future Annulus UI** | Full vision: chat + context pane + graph/trace/swarm views | v1.0 target |
| **Notebooks / CI / bots** | Batch eval, automation | Ad hoc |

**Engine boundaries (stable):**

- Clients talk to the **gateway** (`apps/gateway`), not packages directly.
- **Chat** uses OpenAI-compatible `/v1/chat/completions` and `/v1/models` ([ADR-003](adr-003-openai-compatible-gateway.md)).
- **Agent logic** stays in `AgentRuntime` (`packages/runtime`); clients do not implement tool loops or retrieval injection.
- **Workspace scope** is always via `ANNULUS_WORKSPACE_ROOT`; clients do not bypass the tool sandbox.

**Future API extensions** (non-breaking additions):

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/traces/{trace_id}` | Span tree for run timeline UI |
| `GET /v1/index/status` | Index stats, chunk counts, graph coverage |
| `POST /v1/agents/run` | Long-running swarm jobs (optional; interactive chat remains on `/v1/chat/completions`) |

**Annulus UI (v1.0 direction):**

- Local web app or desktop shell (Tauri/Electron) against `localhost:8080`.
- Layout: main chat/agent thread; side panels for retrieval hits, file snippets, graph visualization, trace timeline.
- UI is **observability and control**; it does not duplicate orchestration logic embedded in the gateway.

## Consequences

**Positive**

- IDE MVP does not constrain long-term UX.
- Same engine serves Continue today and a rich UI tomorrow.
- Clear extension path for trace/index APIs without forking the agent loop.

**Negative**

- v1 UI is substantial product work; engine features (graph, swarm, streaming tools) should lead UI, not follow it.
- Additional API surface requires versioning and auth discipline (reuse gateway API key).

## References

- [vision.md](vision.md)
- [adr-003-openai-compatible-gateway.md](adr-003-openai-compatible-gateway.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-016-typescript-client-layer.md](adr-016-typescript-client-layer.md) — client-layer language and `clients/` layout (engine stays Python)
- `apps/gateway/`
- `docs/continue-config.example.yaml`
