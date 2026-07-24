# ADR backlog plan prompt

**Milestone:** post-v0.3.0 (tag `v0.3.0`)  
**Last updated:** 2026-07-22  
**Scope:** Draft Proposed ADRs 017–024; ADR-016 is reserved for [TypeScript client-layer strategy](../architecture/adr-016-typescript-client-layer.md).

---

Use this file as the task spec for a Claude Code **`/plan`** session (or `--permission-mode plan`). Read the whole file, then follow **Your task** below. Do **not** implement runtime code unless the human explicitly approves execution after reviewing your plan.

## Context

Annulus is a local-first, Python `uv` monorepo agentic platform. **v0.3.0** shipped: git-aware index watch, trace CLI, git tools, eval runbook, Continue/Gemma integration, ChatDescriber title passthrough.

Read these first:

- [`docs/architecture/vision.md`](../architecture/vision.md) — roadmap and principles
- [`docs/architecture/reviews/2026-07-13-pre-v0.3-close-ai-review.md`](../architecture/reviews/2026-07-13-pre-v0.3-close-ai-review.md) — gap analysis with a **recommended ADR scheme** (sections *Recommended new ADRs* and *Top findings*)
- Existing ADRs [`adr-001`](../architecture/adr-001-monorepo-uv.md) through [`adr-016`](../architecture/adr-016-typescript-client-layer.md)
- Open v0.4 gateway prep: GitHub **#50** (OpenAPI/Pydantic for chat), **#51** (`GET /v1/index/status`, `GET /v1/traces/{trace_id}`)
- Open trace: **#40** (`parent_span_id` nested spans)

## Your task (plan mode — do NOT implement runtime code)

Produce a structured plan to close the architectural gaps identified in the July 2026 review by **drafting Proposed ADRs**, updating vision/index docs, and proposing **GitHub issues** — without writing application code.

### 1. Renumber the review’s ADR recommendations

The review proposed ADR-016–023 for non-TS topics. **ADR-016 is TypeScript client layer.** Renumber as:

| New ADR | Topic (from review) |
|---------|---------------------|
| **017** | Skill primitive (Tool ↔ Skill ↔ Agent boundary) |
| **018** | Agent identity & configuration (roles, prompts, memory scope, permissions) |
| **019** | Permission & capability authorization model |
| **020** | Data-egress & compliance policy (ITAR / ZDR / frontier boundaries) |
| **021** | Plan-before-act interaction protocol |
| **022** | Per-project / per-agent policy (`.annulus/config.yaml`) |
| **023** | Provenance & evaluation data model (distinct from observability traces) |
| **024** | Scientific workload primitives (notebooks, data loaders, non-code retrieval) |

For each ADR draft, follow the quality bar of strong existing ADRs (006, 013, 014, 015, 016):

- Status: **Proposed**
- Context (measured problem tied to vision pillars)
- Decision + non-goals
- Consequences (positive/negative)
- Open questions
- Cross-links to related ADRs and current code paths where relevant

Do **not** mark anything **Accepted** unless it is already implemented in code.

### 2. ADR process hygiene

Propose (as part of the plan):

- A minimal [`docs/architecture/adr-template.md`](../architecture/adr-template.md) (Context / Decision / Consequences / Open questions / References)
- Whether to add dates or *Supersedes* fields to new ADRs
- How to distinguish **Proposed** vs **Deferred** vs **Accepted** in the vision ADR table

### 3. Align with current reality (v0.3.0)

Each new ADR must explicitly state:

- What **already exists** in code (e.g. single `AgentRuntime`, tool sandbox path check, flat traces, CLI bypassing gateway for index/traces, binary frontier escalation)
- What **v0.4 work is already tracked** (#50, #51, ADR-015 hybrid retrieval / `propose_edit` issues #31–33)
- What **must precede** write tools, swarms, or Annulus UI (v1.0 / ADR-016 stages 3–5)

### 4. Issue backlog (titles + labels only — do not create on GitHub unless asked)

For each ADR 017–024, suggest:

- One umbrella **documentation** issue (ADR merge PR), OR one issue per ADR if cleaner
- Separate **implementation** issues only where concrete work is implied — with suggested milestone labels (`v0.4`, `v0.5`, `v0.7`, `v1.0`)
- Link to existing issues where they overlap (#40 → provenance/nesting; #50/#51 → client contract)

Prioritize **when each ADR first blocks real work**, not when all of it ships:

- Permissions + egress → before `propose_edit` / write tools
- Plan-before-act → before high-agency autonomous writes
- Skills + agent config → before swarm orchestration (ADR-008)
- Scientific primitives → v0.5+ but Proposed now to avoid SWE-only ossification

### 5. Vision.md updates (propose diff; do not assume merged)

- Add ADRs 017–024 to the Related ADRs table
- Optionally add eval-symptom → ADR rows where helpful
- Keep v0.3 marked ✅ shipped; v0.4 unchanged except cross-links

### 6. Deliverables format

Return:

1. **Executive summary** (≤1 page): top 5 architectural gaps and recommended sequencing across v0.4–v1.0
2. **ADR outline per number (017–024)**: title, 3–5 bullet decision, dependencies, first milestone
3. **Full draft text** for ADRs **017, 019, and 020** only (highest risk: skills boundary, permissions, egress) — others can be outlines if token-limited
4. **Proposed PR structure**: branch name, commit message, file list
5. **Issue list**: title, labels, 2-sentence body, links — ready to paste into GitHub

Optional: save your approved plan output to `docs/plans/sessions/YYYY-MM-DD-post-v030-adr-backlog-plan.md`.

## Constraints

- **No Python/TypeScript implementation** in this pass
- **No rewriting** ADR-016 or changing v0.3 release artifacts
- Preserve Annulus invariants: engine in Python, clients via gateway, `.annulus/` workspace scope, traces are observability not chat memory
- Be specific to this repo — cite real files (`packages/runtime/src/annulus_runtime/agent.py`, `packages/tools/`, `apps/gateway/src/annulus_gateway/routes/chat.py`, etc.)
- Flag anything that duplicates or should supersede thin early ADRs (001–003)

## Success criteria

After the human executes your approved plan, a contributor can read ADRs 017–024 + `vision.md` and understand **what to build next and why**, without re-reading the 2026-07-13 review markdown.

## Claude Code invocation

```text
/plan
Read docs/plans/adr-backlog-plan-prompt.md and execute that task.
Do not implement runtime code unless I approve the plan.
```
