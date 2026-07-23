# Status: Proposed
**Date:** 2026-07-22

## Context

`TraceStore` (`packages/trace/src/annulus_trace/store.py`) is the strongest-implemented
pillar in the review — real span tracing (`chat.completions`, `agent.iteration`,
`retrieval.search`, `tool.*`), a trace CLI (`annulus traces list|show|last`), and an
`X-Annulus-Trace-Id` correlation header. But traces are explicitly **observability,
not memory or provenance** ([ADR-004](adr-004-retrieval-tools-agent-loop.md),
`CLAUDE.md`: "traces are for debugging/eval, never replayed into prompts") — and two
concrete facts confirm the gap the review calls out:

1. **`parent_span_id` is dead.** The schema has the column (`store.py:25,68`),
   `start_span(..., parent_span_id=None)` accepts it (`store.py:101-116`), and
   `build_span_tree` (`store.py:253-275`) already renders nested trees — but every
   span-creation call site in the runtime passes only `trace_id`: `agent.py:177-181,
   251-255, 395-399, 440-444` and `chat.py:53-65`. Every span is a root today; the
   nesting UI is unreachable. This is issue **#40**.
2. **Attributes are truncated by design**, which is correct for an observability tool
   but wrong for a provenance/eval-export source: `query[:200]` (`agent.py:303`),
   `output[:8000]` on `ripgrep` (`executor.py:80`), and `truncate_output(...)` on
   `git_status`/`git_diff` (`executor.py:96,124`). A faithful input→output→provenance
   record cannot be reconstructed from `traces.db` as it exists today.

Separately, [ADR-015](adr-015-local-swe-assistant-v04.md) already commits to a
"v0.4-C" milestone ("eval runbook, bundled Continue config, index watch + re-embed
operational") that implies a prompt-matrix/regression eval suite, but no ADR
specifies what data model that suite consumes — the review notes eval today is
"manual dogfooding + `scripts/probe_ollama_tools.py`," not a committed harness.

## Decision

**Keep traces and provenance as two distinct stores with two distinct purposes** —
this ADR does not change the existing "traces are observability, never replayed"
invariant; it adds a second, deliberately un-truncated record next to it, not a
replacement.

**Step 1 (small, mechanical, do first — closes #40):** wire `parent_span_id` through
`AgentRuntime`. Every span created inside an iteration or tool call should pass the
enclosing `agent.iteration` (or `chat.completions`) span's id as `parent_span_id`.
No schema change needed — `store.py` already supports it. This alone makes
`build_span_tree` render real trees and is the prerequisite for
[ADR-008](adr-008-agent-swarm-orchestration.md)'s multi-agent parent/child
provenance (an orchestrator span parenting worker-run spans).

**Step 2: a provenance record**, separate from `traces.db`. Opt-in (not on by
default, to avoid unbounded disk growth from untruncated tool output on every run),
written to `.annulus/provenance/` (or an `annulus traces export --provenance`
command materializing one from a trace tree plus the untruncated inputs captured at
call time). A provenance record for one run captures: full retrieved-chunk list
(not just hit counts), full tool call arguments and *untruncated* output, the
resolved model profile and any escalation decision
([ADR-020](adr-020-data-egress-compliance-policy.md) denial/grant), and the final
response — enough to replay or use as SFT/RL export input, which `traces.db`'s
truncated attributes cannot support.

**Step 3: eval-suite data model.** Define the prompt-matrix/regression format
[ADR-015](adr-015-local-swe-assistant-v04.md)'s v0.4-C milestone needs: a committed
set of `(prompt, workspace_fixture, expected_signal)` cases, run against
`scripts/probe_ollama_tools.py`-style tooling, scored against provenance records
(not raw traces) so eval has faithful input/output to grade against.

**Non-goals:** no automatic PII/secret scrubbing of provenance records in this pass
(untruncated tool output may contain sensitive workspace content — this ADR flags
the risk but defers a scrubbing policy, which should probably live alongside
[ADR-020](adr-020-data-egress-compliance-policy.md)'s egress policy rather than be
invented here); no training pipeline itself (SFT/RL export format is *shaped* to
support this, not built here); no change to trace truncation behavior — `traces.db`
stays a lightweight observability tool.

## Consequences

**Positive**

- `parent_span_id` wiring is low-risk, immediately actionable, and unblocks two
  things at once: readable trace trees today, and
  [ADR-008](adr-008-agent-swarm-orchestration.md) multi-agent provenance later.
- Cleanly separating provenance from traces avoids the failure mode of either (a)
  bloating `traces.db` with untruncated data it was never designed to hold, or (b)
  truncating provenance data the way traces are truncated, making it useless for
  eval/export.
- Gives [ADR-015](adr-015-local-swe-assistant-v04.md)'s already-Proposed v0.4-C eval
  runbook a concrete data model to build against instead of an implied one.

**Negative**

- A second store (`.annulus/provenance/`) is more surface area under `.annulus/` to
  document, version, and eventually garbage-collect (untruncated tool output across
  many runs is not small).
- Opt-in-only provenance means it won't exist for historical runs — eval/export work
  can only use provenance captured after this ships, not retroactively from existing
  `traces.db` data.
- Untruncated capture raises the same data-sensitivity question
  [ADR-020](adr-020-data-egress-compliance-policy.md) raises for egress, but for
  local disk storage instead of network egress — needs its own answer, flagged here
  as an open question rather than resolved.

## Open questions

- Provenance storage format — SQLite table alongside `traces.db` (reuse
  infrastructure, risk schema coupling) or a separate append-only file format (e.g.
  JSONL per run, simpler to export/scrub, harder to query)?
- Should provenance capture be opt-in per-request (a header/flag) or opt-in per
  project ([ADR-022](adr-022-per-project-agent-policy.md) config field)?
- Retention/garbage-collection policy for provenance records, given untruncated tool
  output accumulates faster than truncated trace attributes?
- Does [ADR-021](adr-021-plan-before-act-protocol.md)'s pending-plan state get
  persisted here, or does it need its own (likely short-lived, non-provenance)
  storage?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-008-agent-swarm-orchestration.md](adr-008-agent-swarm-orchestration.md)
- [adr-013-model-tool-compatibility.md](adr-013-model-tool-compatibility.md)
- [adr-015-local-swe-assistant-v04.md](adr-015-local-swe-assistant-v04.md)
- [adr-019-permission-capability-model.md](adr-019-permission-capability-model.md)
- [adr-020-data-egress-compliance-policy.md](adr-020-data-egress-compliance-policy.md)
- [adr-021-plan-before-act-protocol.md](adr-021-plan-before-act-protocol.md)
- `packages/trace/src/annulus_trace/store.py`
- `packages/runtime/src/annulus_runtime/agent.py`
- `apps/gateway/src/annulus_gateway/routes/chat.py`
