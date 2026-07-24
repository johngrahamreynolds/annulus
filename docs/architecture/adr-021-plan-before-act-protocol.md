# Status: Proposed
**Date:** 2026-07-22

## Context

`grep -i "plan mode|planning"` returns zero hits in `.py` source (confirmed this
session). `AgentRuntime._run_tool_loop` (`packages/runtime/src/annulus_runtime/agent.py:367-470`)
and its streaming twin (`agent.py:120-279`) run fully autonomously up to
`max_iterations` (default 8, `config.py:41`), executing every `tool_calls` entry the
model returns via `self.tools.execute(...)` (`agent.py:445`) with no human checkpoint
of any kind. Today this is low-risk because all four tools
(`read_file`, `ripgrep`, `git_status`, `git_diff`) are read-only.

Pillar 5 of the review ("plan-before-act interaction model") has essentially zero
coverage — the closest existing artifact is [ADR-008](adr-008-agent-swarm-orchestration.md)'s
"orchestrator decomposes goal into a structured plan," which is about task
decomposition for swarms, not a human approval gate for individual actions. Execution
*logging* exists (traces) but logging is not the same as an approve/modify/reject
checkpoint before an action runs.

This becomes urgent, not hypothetical, the moment `propose_edit` (v0.4-B,
[ADR-015](adr-015-local-swe-assistant-v04.md), issues #31-33) ships an `apply` path —
[ADR-015](adr-015-local-swe-assistant-v04.md) already commits to "propose, don't
apply" as the *default*, but doesn't specify what the *optional explicit apply*
confirmation flow actually looks like end-to-end, across both control planes
(Pillar 6: CLI and IDE/gateway).

## Decision

Define a **Plan**: an ordered list of proposed tool calls (today, in practice, this
will usually be a single `apply`-mode call, but the object supports more) emitted by
the agent *before* execution, with an explicit state machine:

```
proposed → approved   → (loop resumes, tool executes)
         → modified    → (re-propose with edits, back to proposed)
         → rejected    → (loop ends or agent adapts, tool never executes)
```

**Gating rule:** only [ADR-019](adr-019-permission-capability-model.md)'s `apply`-mode
tool calls require a Plan/approval step. `propose`-mode calls — today's four
read-only tools, and `propose_edit` in its default propose-only mode — execute exactly
as they do today, no new checkpoint, no UX change for the current happy path. This is
deliberate: the review's Pillar-5 concern is about irreversible/high-agency actions,
not about slowing down read-only retrieval-and-inspect workflows.

**Surface (Pillar 6 — both control planes identically):**

- **Gateway/`/v1/chat/completions`**: extends, not forks, the existing contract. A
  turn that would execute an `apply`-mode call instead returns/streams a plan-proposal
  payload (new field alongside the existing `annulus` metadata block for
  non-streaming; a new SSE event type for streaming) and pauses. A follow-up request
  (new endpoint, e.g. `POST /v1/plans/{plan_id}/resolve` with `approved | modified |
  rejected`) resumes the loop — this endpoint also closes part of the "CLI/gateway
  bypass" gap [ADR-016](adr-016-typescript-client-layer.md) already flags for
  `index`/`traces`, by giving the plan-resolution flow one real HTTP contract instead
  of an ad hoc client-side prompt.
- **CLI**: `annulus chat` interactive mode prints the proposed plan and prompts
  y/n/edit before calling the resolve endpoint — same underlying API as the gateway
  surface, no parallel logic.

`AgentRuntime._run_tool_loop` gets a plan-emission step immediately before the first
`apply`-mode call in a run; on `approved`, the loop resumes exactly where it left off
using the existing iteration/tool-execution code path — this ADR does not change how
tools execute once approved, only what happens immediately before.

**Non-goals:** this ADR does not define swarm-level planning (multi-agent task
decomposition is [ADR-008](adr-008-agent-swarm-orchestration.md)'s concern, and may
build on this primitive later, but a single-agent apply-mode checkpoint is the
in-scope unit here); no plan *editing* UI beyond accepting a modified tool-call
payload back from the client; no automatic/policy-based auto-approval in this pass
(every `apply`-mode call requires an explicit human response — auto-approval rules,
if ever added, are a follow-up).

## Consequences

**Positive**

- Closes the review's Pillar 5 gap directly and is the named safety mechanism the
  ITAR/scientific framing in `vision.md` calls for before any high-agency autonomous
  writes.
- Read-only workflows (today's entire tool surface) are completely unaffected — no
  regression in current UX.
- Reuses the existing `/v1/chat/completions` contract shape rather than inventing a
  parallel "agent run" API, keeping [ADR-006](adr-006-multi-client-architecture.md)'s
  single-contract principle intact.

**Negative**

- A new stateful concept (`Plan`, pending across requests) in an otherwise
  server-side-stateless gateway (`CLAUDE.md`: "Gateway is stateless — no server-side
  chat history") — needs a small, explicitly-scoped exception (pending plans, not
  chat history) documented clearly so it doesn't erode that invariant by precedent.
- Two round-trips (propose, then resolve) for every `apply`-mode action adds latency
  and complexity clients must handle correctly, unlike today's single-request/response
  tool loop.
- CLI and gateway both need to implement the resolve flow correctly — a second place
  the "both control planes get the same feature" discipline can drift
  ([ADR-016](adr-016-typescript-client-layer.md) flags the analogous risk for
  index/traces parity).

## Open questions

- Where does the pending `Plan` state live given the gateway is otherwise stateless —
  in-memory keyed by `plan_id` with a TTL (simplest, lost on gateway restart) or
  persisted (`.annulus/`, alongside traces)? Persisting ties naturally into
  [ADR-023](adr-023-provenance-evaluation-data-model.md)'s provenance record.
- Synchronous (client holds the HTTP connection open pending approval) vs. async
  (propose returns immediately, loop suspends, a separate call resumes) — shared
  decision with [ADR-019](adr-019-permission-capability-model.md)'s open question on
  the same axis.
- Does a rejected plan let the agent retry with a different approach automatically,
  or does the turn simply end?
- Should [ADR-018](adr-018-agent-identity-configuration.md) let a specific agent role
  declare itself pre-trusted (skip the plan step) for constrained, low-risk
  deployments — and if so, is that itself a capability
  ([ADR-019](adr-019-permission-capability-model.md)) or a separate flag?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-006-multi-client-architecture.md](adr-006-multi-client-architecture.md)
- [adr-008-agent-swarm-orchestration.md](adr-008-agent-swarm-orchestration.md)
- [adr-015-local-swe-assistant-v04.md](adr-015-local-swe-assistant-v04.md)
- [adr-016-typescript-client-layer.md](adr-016-typescript-client-layer.md)
- [adr-018-agent-identity-configuration.md](adr-018-agent-identity-configuration.md)
- [adr-019-permission-capability-model.md](adr-019-permission-capability-model.md)
- [adr-023-provenance-evaluation-data-model.md](adr-023-provenance-evaluation-data-model.md)
- `packages/runtime/src/annulus_runtime/agent.py`
- `apps/gateway/src/annulus_gateway/routes/chat.py`
