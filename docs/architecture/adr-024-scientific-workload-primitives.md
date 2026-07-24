# Status: Proposed
**Date:** 2026-07-22

## Context

`vision.md` frames Annulus as a platform for "**engineering and scientific
research**," and Pillar 8 of the review names notebooks, data loaders, simulations,
and bib files as long-term targets. In practice, **100% of implemented capability is
SWE-shaped**: the tool registry is `read_file`/`ripgrep`/`git_status`/`git_diff`
(`packages/tools/src/annulus_tools/registry.py`), retrieval chunking is a naive
char/line window with no non-code awareness (`packages/retrieval` — flagged in
[ADR-009](adr-009-hybrid-retrieval-embeddings.md) as needing AST-aware code splits, a
code-specific concern, not a scientific one), and the concrete roadmap through v0.4 is
explicitly "local SWE assistant" ([ADR-015](adr-015-local-swe-assistant-v04.md)).

The review's own warning is direct: "the pillar warns against 'retrofitting onto a
coding-only platform,' yet the current trajectory is exactly that through at least
v0.4." The risk isn't that v0.4 is SWE-focused — that's a reasonable place to prove
the engine — it's that primitives being designed *right now* (the tool registry
shape, the chunker, [ADR-017](adr-017-skill-primitive.md)'s skill schema, the
retrieval scope concept in [ADR-018](adr-018-agent-identity-configuration.md)) could
silently bake in code-only assumptions before any non-code workload has ever
exercised them, making a later retrofit far more expensive than validating early.

## Decision

Write this ADR now, **specifically to hold the SWE-only trajectory accountable**, but
scope the actual work as a **spike, not a platform commitment** — proportionate to
the fact that v0.4/v0.5 remain SWE-focused by design.

**First concrete validation (v0.5+, non-blocking, parallel to the SWE track):**

- One new read-only tool: `read_notebook` — parses `.ipynb` cell structure (code +
  markdown + outputs) without executing anything, returned the same way `read_file`
  returns file content today (`registry.py`/`executor.py` pattern, same sandbox
  check).
- One chunker extension: non-code chunking for notebooks, markdown-with-math, and
  bib/citation files, so FTS5 (and later hybrid retrieval,
  [ADR-009](adr-009-hybrid-retrieval-embeddings.md)) can actually index a research
  repo meaningfully instead of treating a `.ipynb` as an opaque blob or naively
  line-chunking JSON.
- Package the above as an [ADR-017](adr-017-skill-primitive.md) skill (a
  "research-repo" skill bundling `read_notebook` + `ripgrep` + a prompt fragment
  tuned for citation/notebook context) rather than hardcoding a new `AgentRuntime`
  code path — this validates ADR-017's boundary claim ("new domain workflows become
  workspace-authored YAML") on a real non-SWE example, which is also useful evidence
  for whether that ADR's design actually holds up outside coding use cases.
- Validate against one real research repo (dogfooding, same discipline
  [ADR-014](adr-014-incremental-index-watch.md)'s "~280 files, ~5 min" measurement
  came from) — not synthetic fixtures only.

**Explicit non-goals for this pass:** notebook or simulation **execution** (running
cells, running a simulation) — any execute-capable tool needs
[ADR-019](adr-019-permission-capability-model.md)'s `apply`-mode gate and
[ADR-021](adr-021-plan-before-act-protocol.md)'s approval flow, neither of which this
ADR builds; data loaders for structured scientific formats (HDF5, FITS, etc.) beyond
what a read-only tool needs to show file structure; any hardcoded "physics mode" or
discipline-specific behavior baked into `AgentRuntime` — reaffirms
[ADR-011](adr-011-governed-self-improvement.md)'s domain-agnostic-engine tenet:
discipline is workspace content + skills, never core-engine logic.

## Consequences

**Positive**

- Gives the review's Pillar 8 warning a concrete, scheduled response instead of
  leaving it as an unaddressed risk through v0.4/v0.5.
- A small, read-only spike is low-cost insurance against expensive retrofits of the
  tool registry, chunker, and skill schema later.
- Doubles as a real-world test of [ADR-017](adr-017-skill-primitive.md)'s
  tool/skill/agent boundary on a genuinely different workload than the SWE case it
  was designed against.

**Negative**

- Splits attention/roadmap focus during a period (v0.4/v0.5) that's already
  committed to SWE-assistant delivery — must stay explicitly non-blocking or it
  competes with `propose_edit`/hybrid-retrieval work for the same engineering time.
- One notebook tool and one chunker extension is a thin validation — it can
  demonstrate the primitives *don't* obviously break on non-code content, but can't
  prove they're *right* for the full scientific workload space (simulations, data
  pipelines) that Pillar 8 ultimately wants.
- Non-code chunking quality is a real open problem (markdown-with-math and notebook
  cell boundaries are not as well-trodden as code AST splitting) — risk of shipping a
  chunker that's "good enough to not embarrass the spike" but not actually good.

## Open questions

- Which research repo (real or purpose-built fixture) is the validation target, and
  who owns dogfooding it — mirrors the same question the SWE track already answers
  via the eval devcontainer, but no equivalent exists for a non-code workspace yet.
- Does `read_notebook` need cell-output truncation/size limits analogous to
  `ripgrep`'s `output[:8000]` (`executor.py:80`), given notebook outputs (plots,
  large dataframes) can be far larger than typical code file content?
- Should non-code chunking share `packages/retrieval`'s existing chunker module with
  a format-dispatch branch, or live as a genuinely separate chunking strategy
  selected by file type — affects how much [ADR-009](adr-009-hybrid-retrieval-embeddings.md)'s
  planned AST-aware code-chunking work and this spike can share code.
- At what point (what signal) does this graduate from "spike" to a scheduled
  milestone with its own ADR-015-style phased plan?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-009-hybrid-retrieval-embeddings.md](adr-009-hybrid-retrieval-embeddings.md)
- [adr-011-governed-self-improvement.md](adr-011-governed-self-improvement.md)
- [adr-014-incremental-index-watch.md](adr-014-incremental-index-watch.md)
- [adr-015-local-swe-assistant-v04.md](adr-015-local-swe-assistant-v04.md)
- [adr-017-skill-primitive.md](adr-017-skill-primitive.md)
- [adr-019-permission-capability-model.md](adr-019-permission-capability-model.md)
- [adr-021-plan-before-act-protocol.md](adr-021-plan-before-act-protocol.md)
- `packages/tools/src/annulus_tools/registry.py`
- `packages/retrieval/`
