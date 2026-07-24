# Proposed PR structure — ADR backlog 017–024

## Branch

```
docs/adr-backlog-017-024
```

(already created and committed locally — commit `3d66073`)

## Files changed

- `docs/architecture/adr-template.md` (new)
- `docs/architecture/adr-017-skill-primitive.md` (new)
- `docs/architecture/adr-018-agent-identity-configuration.md` (new)
- `docs/architecture/adr-019-permission-capability-model.md` (new)
- `docs/architecture/adr-020-data-egress-compliance-policy.md` (new)
- `docs/architecture/adr-021-plan-before-act-protocol.md` (new)
- `docs/architecture/adr-022-per-project-agent-policy.md` (new)
- `docs/architecture/adr-023-provenance-evaluation-data-model.md` (new)
- `docs/architecture/adr-024-scientific-workload-primitives.md` (new)
- `docs/architecture/vision.md` (edited — Status column added to Related ADRs
  table, 8 new rows, 4 new eval-signal rows, v0.4 roadmap row cross-link)

## Commit message

```
docs: draft ADRs 017-024 architecture backlog (post-v0.3 gap closure)

Adds Proposed ADRs for the skill primitive, agent identity, permission
model, data-egress policy, plan-before-act protocol, per-project policy,
provenance data model, and scientific workload primitives, per the
2026-07-13 architecture review. Adds an ADR template and a Status
column on vision.md's ADR table.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

## PR title

```
docs: ADR backlog 017–024 (post-v0.3 architecture gaps)
```

## PR description

```markdown
## Summary

- Drafts Proposed ADRs 017–024, closing the gap the 2026-07-13 architecture
  review identified: agent governance (skills, agent-as-config, permissions,
  plan-before-act, data egress) is undocumented and unenforced in code, right
  as v0.4 is about to ship the first write-capable tool (`propose_edit`,
  #31–33).
- Adds `docs/architecture/adr-template.md` and a Status column on
  `vision.md`'s Related ADRs table (ADR process hygiene).
- No Python/TypeScript code changes. ADR-016 and v0.3 release artifacts are
  untouched.

**Renumbering note:** the review proposed ADR-016–023 for these topics;
ADR-016 is reserved for the already-merged TypeScript client-layer ADR, so
everything here shifts by one (017–024).

**Top 5 gaps addressed** (see each ADR's Context section for file/line
grounding):
1. Skills and agent-as-config don't exist (017, 018) — blocks swarm
   orchestration (ADR-008).
2. No permission, plan-before-act, or egress model (019, 020, 021) —
   highest risk given the ITAR/NASA framing in vision.md.
3. No per-project policy surface (022) — `.annulus/config.yaml` is currently
   aspirational prose only (ADR-012), never read by code.
4. Observability is strong but isn't provenance (023) — `parent_span_id`
   exists in the trace schema but is never set (closes #40).
5. The platform is coding-only in practice (024) — written now to prevent
   primitives from ossifying before any scientific workload exercises them.

**Already-tracked work, cross-linked not duplicated:** #50 (typed chat
contract) and #51 (`/v1/index/status`, `/v1/traces/{id}`) are covered by
ADR-016's existing staged sequencing; no new ADR needed for those.

## Test plan

Documentation-only change.

- [ ] Every new ADR follows `adr-template.md`'s section order
      (Status/Context/Decision/Consequences/Open questions/References)
- [ ] Every `[adr-0NN-...]` cross-link in the new files resolves to a real
      file in `docs/architecture/`
- [ ] `vision.md`'s new Status column and ADR rows render correctly, all
      links resolve
- [ ] Re-check `docs/architecture/adr-*.md` for numbering collisions
      immediately before merge (no ADR 017–024 should exist from another
      branch)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
