# Status: Proposed

## Context

v0.3 delivers a **streaming agent** with FTS retrieval, server-side read/search tools, **git_status / git_diff**, git-aware index watch, trace CLI, and Continue integration ([ADR-004](adr-004-retrieval-tools-agent-loop.md), [ADR-014](adr-014-incremental-index-watch.md)).

Work environments may lack frontier APIs and commercial AI-IDE products. v0.4 targets a **local, IDE-integrated SWE assistant**: grounded answers, proposed edits, and inline diffs via Continue — without building Annulus UI yet ([ADR-006](adr-006-multi-client-architecture.md)).

Hybrid retrieval ([ADR-009](adr-009-hybrid-retrieval-embeddings.md)) improves recall; **propose_edit** (v0.4) closes the loop from search to change. Read-only git tools shipped in v0.3 so the agent can inspect dirty trees before ripgrep or edits.

## Decision

v0.4 north star: **local Cursor-class SWE assistant** on Continue + CLI, backed by the same `AgentRuntime`.

**Three milestones (ship in order):**

| Milestone | Focus |
|-----------|--------|
| **v0.4-A** | Hybrid retrieval — embed profile, vector store, merge with FTS5, trace hit metadata |
| **v0.4-B** | SWE edit surface — `propose_edit` (patch/diff, propose-only default), Continue edit/apply role eval |
| **v0.4-C** | Team rollout — eval runbook, bundled Continue config, index watch + re-embed operational |

**v0.3 (shipped / shipping):** `git_status`, `git_diff` — read-only, sandboxed `git -C workspace`; traced as `tool.git_status` / `tool.git_diff`.

**Edit / apply policy ([ADR-011](adr-011-governed-self-improvement.md)):**

- Default **propose, don't apply** — tools return unified diff or patch text; no silent writes.
- Optional explicit apply (Continue Apply button or tool flag) after user confirmation.
- Use v0.3 `git_status` / `git_diff` before proposing edits on dirty trees.

**Continue integration:**

- Chat: existing agent loop + hybrid retrieval injection.
- Edit / apply: Continue `roles` on Annulus profiles (`docs/continue-config.example.yaml`); model output must match Continue edit stream expectations for inline diffs.
- Server-side `propose_edit` complements Continue edit role (agent loop + CLI); both may coexist during eval.

**Index lifecycle:**

- Incremental watch ([ADR-014](adr-014-incremental-index-watch.md)) must **re-embed changed chunks** in v0.4, not only FTS rows.
- Full rebuild when embed model or chunk strategy changes.

**Out of v0.4 scope:**

- GraphRAG ([ADR-010](adr-010-graphrag-lite.md)) — v0.5
- Remote lab GPU profiles ([ADR-007](adr-007-remote-compute-profiles.md)) — v0.6
- Annulus dedicated UI — v1.0
- Target-native packaged sidecar image — post–v0.4 unless team rollout demands it

## Consequences

**Positive**

- Delivers practical SWE value on locked-down machines (local models only).
- Reuses Continue as frontend; no v1 UI blocker.
- Hybrid retrieval + edit loop generalizes later to research repos.
- v0.3 git tools ground the agent on working-tree state before v0.4 propose_edit.

**Negative**

- Edit quality depends on local model (Gemma4); eval matrix required.
- Two edit paths (Continue edit role vs server-side tool) need clear eval ownership until converged.

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-009-hybrid-retrieval-embeddings.md](adr-009-hybrid-retrieval-embeddings.md)
- [adr-011-governed-self-improvement.md](adr-011-governed-self-improvement.md)
- [adr-014-incremental-index-watch.md](adr-014-incremental-index-watch.md)
- `packages/tools/`, `packages/retrieval/`, `packages/runtime/`
