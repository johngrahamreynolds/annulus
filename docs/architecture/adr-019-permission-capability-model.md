# Status: Proposed
**Date:** 2026-07-22

## Context

The only access-control concept in the codebase today is a single path-containment
check in `ToolExecutor._resolve_path` (`packages/tools/src/annulus_tools/executor.py:29-33`):
it resolves a requested path against `self.root` and raises if it escapes the
sandbox. No allowlist of tool *names*, no per-agent/per-session scoping, no
human-approval gate exists anywhere.

`ToolsConfig.allowed_commands` (`config.py:59-61`, default `["rg"]`, mirrored in
`default.yaml:56-59`) *looks* like a permission control but is dead config —
`executor.py:53` hardcodes the `rg` invocation directly and never reads
`settings.tools.allowed_commands`. This is a concrete, fixable gap, not just a design
gap.

`AgentRuntime._run_tool_loop` (`agent.py:367-470`) executes every `tool_calls` entry
the model returns via `self.tools.execute(...)` (`agent.py:445`) with zero gating
beyond the path sandbox, for up to `max_iterations` (default 8, `config.py:41`)
iterations.

Today's four tools (`read_file`, `ripgrep`, `git_status`, `git_diff`) are all
read-only, which is why this has been low-risk so far. That changes with
`propose_edit` (v0.4-B, [ADR-015](adr-015-local-swe-assistant-v04.md), issues
#31-33) — the first tool that can produce a diff intended for application — and again
with [ADR-017](adr-017-skill-primitive.md) skills and
[ADR-018](adr-018-agent-identity-configuration.md)/[ADR-008](adr-008-agent-swarm-orchestration.md)
agents/swarms, each of which needs a tool allowlist. Zero hits for "permission"
anywhere in `.py` source — this is a from-scratch design.

## Decision

Introduce a **capability** as the unit of authorization: `{tool_name, optional path
scope, optional mode (read | propose | apply)}`. A capability set is attached at
three layers, most-restrictive wins:

1. **Engine default** — today's implicit "all four read-only tools, whole sandbox"
   becomes an explicit default in `config/default.yaml` (`tools.default_capabilities`),
   replacing the currently-unenforced `allowed_commands` field with something the
   executor actually reads.
2. **Skill-scoped** ([ADR-017](adr-017-skill-primitive.md)) — a skill's tool
   allowlist is a capability subset requested for the run.
3. **Agent-scoped** ([ADR-018](adr-018-agent-identity-configuration.md)) — an agent
   identity's configured allowlist and path scope; the outer bound skills/requests
   can only narrow, never widen.

`ToolExecutor.execute()` gains a capability check **before** dispatch: reject (traced
as `tool.<name>.denied`) any call whose tool name isn't in the resolved capability
set — additive to `_resolve_path` (`executor.py:29-33`), not a replacement.

**Mode** distinguishes read-only tools (today's four — auto-approved within
capability scope) from mutating tools (`propose_edit` and future write tools):
`propose` mode returns a diff without touching disk (already ADR-015's default —
"propose, don't apply"); `apply` mode requires an explicit approval signal (the gate
itself is defined here; the approve/modify/reject UX is
[ADR-021](adr-021-plan-before-act-protocol.md)).

Every authorization decision is traced (`tool.<name>.granted` / `tool.<name>.denied`)
as a span attribute — immediate debugging value now, feeds
[ADR-023](adr-023-provenance-evaluation-data-model.md)'s provenance record later.

**Non-goals:** no multi-user RBAC (Annulus is single-operator per workspace,
`ANNULUS_API_KEY` gateway-wide); no fine-grained per-file ACLs beyond the existing
sandbox-root scoping; no cryptographic capability tokens — in-process config-driven
authorization, not a distributed security boundary.

## Consequences

**Positive**

- Turns a currently-dead config field (`allowed_commands`) into a real, enforced
  control.
- Gives [ADR-017](adr-017-skill-primitive.md) skills and
  [ADR-018](adr-018-agent-identity-configuration.md) agents a shared enforcement
  point instead of each reinventing tool gating.
- The explicit prerequisite the review calls out before any write-capable tool ships.

**Negative**

- Every tool call gains a capability-resolution step (skill ∩ agent ∩ engine-default)
  — more moving parts than today's single path check.
- Over-narrow capability sets silently degrade legitimate read-only workflows unless
  denial tracing/errors are good, not silent empty results.
- Retrofitting the four existing tools into explicit capabilities is a small breaking
  change to `config/default.yaml`'s shape.

## Open questions

- Capability resolution once per run (agent+skill fixed at start) vs. per tool call
  (dynamic narrowing mid-run)?
- `apply`-mode approval synchronous (blocks the loop pending human response) vs.
  async (propose, end loop, resume via a separate endpoint) — shared decision with
  [ADR-021](adr-021-plan-before-act-protocol.md).
- Engine-default capability set global (`config/default.yaml`) or owned by
  [ADR-022](adr-022-per-project-agent-policy.md) from day one, given ITAR-tier vs.
  prototype-tier projects may sit on the same machine?
- How does capability denial surface to the model — retryable tool error vs. hard
  stop?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-015-local-swe-assistant-v04.md](adr-015-local-swe-assistant-v04.md)
- [adr-017-skill-primitive.md](adr-017-skill-primitive.md)
- [adr-018-agent-identity-configuration.md](adr-018-agent-identity-configuration.md)
- [adr-020-data-egress-compliance-policy.md](adr-020-data-egress-compliance-policy.md)
- [adr-021-plan-before-act-protocol.md](adr-021-plan-before-act-protocol.md)
- [adr-022-per-project-agent-policy.md](adr-022-per-project-agent-policy.md)
- `packages/tools/src/annulus_tools/executor.py`
- `packages/core/src/annulus_core/config.py`
