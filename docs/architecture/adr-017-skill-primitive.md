# Status: Proposed
**Date:** 2026-07-22

## Context

Pillar 4 (tools vs. skills vs. agents) is the weakest-covered pillar in the 2026-07-13
architecture review. "Skill" appears only as a future bullet in
[ADR-011](adr-011-governed-self-improvement.md) (`.annulus/` skills idea) — zero hits
in `.py` source. Today's tools are exactly four hardcoded functions in
`packages/tools/src/annulus_tools/registry.py` (`read_file`, `ripgrep`, `git_status`,
`git_diff`), dispatched in `executor.py:18-27`, gated only by `profile.supports_tools`
([ADR-004](adr-004-retrieval-tools-agent-loop.md)). There is no packaging unit above a
single function call — any multi-step domain workflow ("audit this PR," "arXiv
monitor," "simulation pipeline") must be hardcoded into `AgentRuntime`
(`packages/runtime/src/annulus_runtime/agent.py:66`), which is a single class with no
notion of pluggable capability bundles.

This blocks [ADR-008](adr-008-agent-swarm-orchestration.md) (workers need scoped
capability sets, not "all tools") and Pillar 8 / [ADR-024](adr-024-scientific-workload-primitives.md)
(every new domain capability today means an engine PR, not a workspace artifact).

## Decision

Define **Skill** as a declarative, discoverable bundle: name/description, a prompt
fragment, a tool-name allowlist (subset of the tool registry — see
[ADR-019](adr-019-permission-capability-model.md)), and optional structured
parameters. Skills are data, not code — no new execution path, just a loader that
assembles prompt + tool allowlist per skill.

**Storage:** `.annulus/skills/*.yaml` in the *target* workspace — workspace-scoped
like `.annulus/index.db` / `.annulus/traces.db` today, not embedded in the engine
(`vision.md` principle 1). A `SkillLoader` (new `packages/skills`, or folded into
`packages/runtime`) reads and validates these.

**Boundary (the core of this ADR):**

- **Tool** — a single, stateless, server-executed function with a fixed schema
  (`packages/tools/registry.py`). Doesn't know about goals.
- **Skill** — a named, reusable recipe: scoped prompt + tool allowlist + optional
  params, invoked within a single `AgentRuntime` run. Doesn't spawn agents or persist
  state across turns.
- **Agent** — a configured identity ([ADR-018](adr-018-agent-identity-configuration.md))
  that may load zero or more skills, with its own retrieval scope / model profile /
  permission set. Agents compose into swarms ([ADR-008](adr-008-agent-swarm-orchestration.md));
  skills don't.

Concretely: "run ripgrep" is a tool call. "Audit this PR using rg + git_diff + a fixed
checklist prompt" is a skill. "The security-review agent that owns its own
conversation and can delegate" is an agent.

`AgentRuntime` gains an optional `skills: list[str]` parameter; when set, the runtime
merges each skill's prompt fragment into the system prompt and restricts
`ToolExecutor` to the union of allowlisted tool names — extending the existing
path-level sandbox check (`executor.py:29-33`) with a name-level allowlist, which is
also where [ADR-019](adr-019-permission-capability-model.md) hooks in.

**Non-goals:** no arbitrary code execution inside a skill definition; no skill
composition (skills calling skills) in this pass; no skill marketplace/sharing
mechanism.

## Consequences

**Positive**

- Gives Pillar 4 and Pillar 8 ([ADR-024](adr-024-scientific-workload-primitives.md)) a
  real seam — new domain workflows become workspace-authored YAML, not core-engine
  PRs.
- Composes naturally with [ADR-019](adr-019-permission-capability-model.md)'s tool
  allowlist; unblocks [ADR-018](adr-018-agent-identity-configuration.md)/[ADR-008](adr-008-agent-swarm-orchestration.md)
  by giving agents something concrete to load.

**Negative**

- Another workspace-scoped file format to design, document, and validate (schema
  drift risk, cf. [ADR-014](adr-014-incremental-index-watch.md)'s FTS5 migration pain).
- Skill/tool boundary needs active enforcement — "just needs one more tool" pressure
  will erode it over time without review discipline.
- Adds a load-time step (skill discovery) to `AgentRuntime` startup.

## Open questions

- YAML vs. Markdown+frontmatter for skill files (Claude/OpenClaw-style skills use
  Markdown; Annulus's other workspace config is YAML).
- Explicit skill selection (client requests it, like the `model` field) vs. automatic
  (agent inspects the query and picks) — automatic selection overlaps
  [ADR-018](adr-018-agent-identity-configuration.md)'s role concept.
- Schema version field from day one, given `.annulus/`'s prior breaking FTS5 migration?
- Fail-fast vs. best-effort validation when a skill's tool allowlist references an
  unknown tool name?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-008-agent-swarm-orchestration.md](adr-008-agent-swarm-orchestration.md)
- [adr-011-governed-self-improvement.md](adr-011-governed-self-improvement.md)
- [adr-018-agent-identity-configuration.md](adr-018-agent-identity-configuration.md)
- [adr-019-permission-capability-model.md](adr-019-permission-capability-model.md)
- `packages/tools/src/annulus_tools/registry.py`
- `packages/tools/src/annulus_tools/executor.py`
- `packages/runtime/src/annulus_runtime/agent.py`
