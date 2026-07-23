# Status: Proposed
**Date:** 2026-07-22

## Context

`load_settings()` (`packages/core/src/annulus_core/config.py:149-178`) loads exactly
two files from a single `config_dir`: `config/default.yaml` and `config/models.yaml`,
both shipped with the Annulus engine repo, not the target workspace. There is no code
path anywhere that reads `ANNULUS_WORKSPACE_ROOT/.annulus/config.yaml` — that path is
purely aspirational, mentioned only in [ADR-012](adr-012-target-native-sidecar-deployment.md)'s
prose (`.annulus/config.yaml` sketched as a "conceptual" future setting, lines 29-44)
and in this backlog's own planning doc. This means every policy surface today —
routing (`router.escalation_enabled`), tool defaults (`tools.allowed_commands`,
itself unenforced — see [ADR-019](adr-019-permission-capability-model.md)) — is
**global to the Annulus process**, not scoped to the workspace it happens to be
mounted against.

That's a structural problem for two ADRs in this same backlog:
[ADR-019](adr-019-permission-capability-model.md)'s capability defaults and
[ADR-020](adr-020-data-egress-compliance-policy.md)'s `egress`/`zdr` policy both need
to answer "for *this* project" — an ITAR-tier repo and a personal side-project repo
should not be forced to share one global escalation/permission posture just because
they happen to be indexed by the same Annulus installation.

## Decision

Add `.annulus/config.yaml` as a **project policy overlay**, read by `load_settings()`
when `ANNULUS_WORKSPACE_ROOT/.annulus/config.yaml` exists — the first code path to
actually consume this file. Precedence (highest wins):

```
.annulus/config.yaml   (project policy — diffable, committed with the target repo)
      ↓ overrides
config/default.yaml     (engine default — ships with Annulus)
      ↓
.env                     (secrets and paths only — API keys, ANNULUS_WORKSPACE_ROOT;
                           policy fields do NOT live here, per ADR-011's principle
                           that behavior changes go through reviewable config/workspace
                           artifacts, not opaque env vars)
```

**Initial schema (v1, deliberately minimal):**

```yaml
# .annulus/config.yaml (conceptual, v1 fields only)
schema_version: 1
egress: allowed          # none | zdr_only | allowed — ADR-020
default_capabilities:    # ADR-019 — omit to inherit config/default.yaml's engine default
  - read_file
  - ripgrep
  - git_status
  - git_diff
escalation:
  enabled: true           # overrides router.escalation_enabled for this project only
```

Fields for [ADR-017](adr-017-skill-primitive.md) skill directories,
[ADR-018](adr-018-agent-identity-configuration.md) agent directories, and future
[ADR-023](adr-023-provenance-evaluation-data-model.md) provenance settings are
explicitly deferred to a later schema version, not designed in v1 — those already
have their own directory-based discovery (`.annulus/skills/`, `.annulus/agents/`) and
don't strictly need a central config entry to function.

**Versioning:** `schema_version` from day one, learning directly from
[ADR-014](adr-014-incremental-index-watch.md)'s undocumented FTS5 schema break —
`load_settings()` should refuse to silently guess on an unknown/missing
`schema_version` rather than partially apply a malformed overlay.

**Non-goals:** no secrets in this file (API keys stay in `.env`, consistent with
today's split and with [ADR-002](adr-002-host-ollama-docker-apps.md)'s deployment
model); no per-*user* policy (this is per-*project*, matching the existing
single-operator-per-workspace assumption in [ADR-019](adr-019-permission-capability-model.md));
no UI/CLI for editing this file in v1 — it's hand-authored YAML like every other
`.annulus/` and `config/` artifact today.

## Consequences

**Positive**

- Gives [ADR-019](adr-019-permission-capability-model.md) and
  [ADR-020](adr-020-data-egress-compliance-policy.md) the project-scoped home their
  own Open Questions already flag as needed.
- First real implementation of a concept [ADR-012](adr-012-target-native-sidecar-deployment.md)
  has been sketching in prose since it was written — closes an existing
  documentation/code gap, not just a new one.
- Small v1 schema (two-ish real fields) keeps initial implementation and review scope
  tight; the temptation to also fold in skills/agents/provenance config is explicitly
  deferred.

**Negative**

- A config file that lives in the *target* repo's `.annulus/` (gitignored per
  `CLAUDE.md`) means project policy is, by default, **not** committed/shared across a
  team unless someone explicitly un-gitignores it or documents a distribution story —
  worth flagging in the eventual eval runbook.
- Precedence rules (project overlay > engine default > `.env`) need to be documented
  clearly and tested, or debugging "why did this project escalate when I set
  `egress: none`" becomes its own support burden.
- Yet another `.annulus/` artifact contributors need to know about, alongside
  `index.db`, `traces.db`, `index_meta.json`, and (pending) `skills/`, `agents/`.

## Open questions

- Should a missing `.annulus/config.yaml` mean "inherit engine defaults" (permissive,
  today's implicit behavior, chosen default here) or "fail closed until a project
  explicitly opts in" — ties directly to [ADR-020](adr-020-data-egress-compliance-policy.md)'s
  identical open question about default `egress`.
- Does the gateway hot-reload this file on change, or only read it at startup /
  per-index-watch-tick (mirroring [ADR-014](adr-014-incremental-index-watch.md)'s
  polling model)?
- Should there be a CLI command (`annulus config show`) to print the fully-resolved
  effective policy (project overlay + engine default merged), given three layers of
  precedence are otherwise hard to reason about from the files alone?
- Multi-root workspaces (if ever supported) — does each root get its own
  `.annulus/config.yaml`, or is this inherently single-workspace-root scoped like
  `ANNULUS_WORKSPACE_ROOT` is today?

## References

- [vision.md](vision.md)
- [adr-011-governed-self-improvement.md](adr-011-governed-self-improvement.md)
- [adr-012-target-native-sidecar-deployment.md](adr-012-target-native-sidecar-deployment.md)
- [adr-014-incremental-index-watch.md](adr-014-incremental-index-watch.md)
- [adr-017-skill-primitive.md](adr-017-skill-primitive.md)
- [adr-018-agent-identity-configuration.md](adr-018-agent-identity-configuration.md)
- [adr-019-permission-capability-model.md](adr-019-permission-capability-model.md)
- [adr-020-data-egress-compliance-policy.md](adr-020-data-egress-compliance-policy.md)
- `packages/core/src/annulus_core/config.py`
