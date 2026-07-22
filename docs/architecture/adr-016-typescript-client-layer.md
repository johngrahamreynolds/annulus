# Status: Proposed

## Context

Annulus's engine (`AgentRuntime`, `ModelRouter`, retrieval, tools, trace) is a Python `uv` workspace monorepo ([ADR-001](adr-001-monorepo-uv.md)) exposed only through an OpenAI-compatible HTTP contract ([ADR-003](adr-003-openai-compatible-gateway.md)). [ADR-006](adr-006-multi-client-architecture.md) already treats every user-facing surface — Continue, the CLI, a future dedicated **Annulus UI** — as a client of that engine, and floats a **Tauri/Electron** desktop shell (both JS/TS-based) as the v1.0 UI direction. No ADR has yet named TypeScript explicitly or said where it would live in this repo.

TypeScript is the default language for the surfaces Annulus doesn't have yet: a rich desktop/web UI, editor extensions, and any SDK a script or bot would import. The question this ADR answers is not "should Annulus have a UI" (ADR-006 already says yes) but **where TypeScript is and isn't appropriate in this stack, and what has to be true of the Python side before it can be added safely.**

Two gaps exist today that matter for this decision:

1. `POST /v1/chat/completions` (`apps/gateway/src/annulus_gateway/routes/chat.py`) parses a raw `dict` from `request.json()` and returns a hand-built dict; it is not wired to the `ChatCompletionRequest` model already defined (unused) in `packages/core/src/annulus_core/types.py`. FastAPI's generated `/openapi.json` therefore has no real schema for this endpoint — there is nothing to generate TypeScript types from yet.
2. ADR-006's rule that "clients talk to the gateway, not packages directly" is already broken by Annulus's own CLI: `annulus index` and `annulus traces` import `annulus_retrieval` / `annulus_trace` in-process and read `.annulus/*.db` off disk, because `GET /v1/index/status` and `GET /v1/traces/{trace_id}` (both listed in ADR-006 as future work) don't exist yet. Any TypeScript client would only get chat parity with Continue, not full CLI parity, until these ship.

## Decision

**TypeScript is adopted only as an edge/client-layer technology, never as a rewrite target for the engine.** The engine — `AgentRuntime`, `ModelRouter`, retrieval/FTS5, `ToolExecutor`, `TraceStore` — stays Python, in the existing `uv` workspace, unconditionally. TypeScript components are pure HTTP consumers of the gateway's `/v1` contract, exactly like Continue is today; they never embed retrieval, tool-loop, or routing logic (reaffirms [ADR-004](adr-004-retrieval-tools-agent-loop.md), [ADR-006](adr-006-multi-client-architecture.md)).

**Sequencing — TypeScript work is gated on Python-side prep, in this order:**

| Stage | Work | Package |
|-------|------|---------|
| 1. Typed contract | Wire `ChatCompletionRequest`/a response model into `chat.py` so `/openapi.json` has a real schema for `/v1/chat/completions` and `/v1/models` | `annulus_core`, `annulus_gateway` |
| 2. API parity | Ship `GET /v1/index/status` and `GET /v1/traces/{trace_id}` (already scoped in ADR-006) so a TS client has the same surface the CLI gets via direct package access | `annulus_gateway` |
| 3. Generated types | Generate TS types from `/openapi.json` (e.g. `openapi-typescript`) instead of hand-maintaining a duplicate schema — regenerate on every gateway schema change | new `clients/` dir (below) |
| 4. Thin SDK (optional) | A minimal TS wrapper package (fetch/SSE client + generated types) for scripts, bots, or a future editor extension | new `clients/` dir |
| 5. Annulus UI | The v1.0 dedicated UI ADR-006 already anticipates — Tauri or Electron, consuming stages 1–4 | new `clients/` dir |

**Repo layout:** TypeScript code lives in a new top-level `clients/` directory, sibling to `apps/` and `packages/`, **outside** the `uv` workspace (`pyproject.toml` members stay Python-only per ADR-001). `clients/` gets its own package manager workspace (pnpm recommended for lockfile + audit ergonomics) and its own CI job, kept fully decoupled from `uv sync`/`pytest`. Exact packaging (single package vs. internal pnpm workspace for SDK + UI) is deferred to a follow-up ADR once stage 4/5 work actually starts — premature to fix now.

**Non-goals (explicit):**

- No rewrite of `AgentRuntime`, `ModelRouter`, retrieval/indexer, `ToolExecutor`, or `TraceStore` in TypeScript, ever, under this ADR. Sqlite FTS5, git-delta indexing, subprocess `ripgrep`/`git`, and the Ollama integration are mature and correct in Python; duplicating that logic in a second runtime buys nothing and reintroduces exactly the "clients reimplement engine logic" failure mode ADR-006 was written to prevent.
- No TypeScript in `apps/` or `packages/` (those stay `uv`-workspace Python per ADR-001); TypeScript is additive under `clients/`, not interleaved with existing members.
- Stage 5 (Annulus UI) timing is unchanged from ADR-006's v1.0 target — this ADR does not pull it forward.

**ITAR-conscious constraint on any Node/TS tooling:** given Annulus's local-first, air-gap-friendly posture ([ADR-002](adr-002-host-ollama-docker-apps.md)), any `clients/` package manager lockfile (`pnpm-lock.yaml`) is committed and auditable exactly like `uv.lock`; build steps must not require network access beyond an initial, reviewable `pnpm install`; no telemetry-phoning-home dependencies (build tools, analytics SDKs) are added without explicit review; and the UI shell (Tauri preferred over Electron for a smaller, more auditable native surface — final choice deferred to the stage-5 ADR) must run fully offline against `localhost:8080` like every other client.

## Consequences

**Positive**

- Engine stays single-source-of-truth in Python; no behavior fork between a "Python agent loop" and a "TS agent loop."
- Fixing the untyped `/v1/chat/completions` route (stage 1) benefits every client, not just future TS ones — it closes a real gap where the API contract exists only in the client's head today.
- Generated types (stage 3) mean the TS side can't silently drift from the gateway's actual schema.
- Clear place (`clients/`) and clear non-goals prevent scope creep into "let's just rewrite the runtime in TS" later.

**Negative**

- Stages 1–2 are real engineering cost (Pydantic wiring, two new endpoints) that must land before any TS code is worth writing — this ADR intentionally blocks stage 3+ on them.
- Two toolchains (`uv`/Python, pnpm/TypeScript) to maintain long-term: two lockfiles, two CI jobs, two audit surfaces.
- Contributors will eventually need JS/TS familiarity for `clients/` work; the user has none yet, so stage 4–5 work implies a real learning curve, not just config.
- Deferring `clients/` internal packaging to a later ADR means this decision is intentionally incomplete on that point.

## Open questions

- Package manager / monorepo tool for `clients/` (plain pnpm workspace vs. Turborepo/Nx) — revisit at stage 4.
- Tauri vs. Electron for the v1.0 UI shell — ADR-006 names both; this ADR doesn't decide.
- Hand-written vs. fully generated SDK (`openapi-typescript` types only vs. a generated client like `orval`/`openapi-fetch`).
- Whether `clients/` ever gets its own CI gate in the same PR pipeline as `packages/`/`apps/`, or stays independently released.

## References

- [vision.md](vision.md)
- [adr-001-monorepo-uv.md](adr-001-monorepo-uv.md)
- [adr-003-openai-compatible-gateway.md](adr-003-openai-compatible-gateway.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-006-multi-client-architecture.md](adr-006-multi-client-architecture.md)
- [adr-002-host-ollama-docker-apps.md](adr-002-host-ollama-docker-apps.md)
- `apps/gateway/src/annulus_gateway/routes/chat.py`
- `packages/core/src/annulus_core/types.py`
