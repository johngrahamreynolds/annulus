# Changelog

All notable changes to Annulus are documented here. Version numbers follow the workspace `pyproject.toml` root package.

## [0.3.0] — 2026-07-22

v0.3 closes the initial Continue/CLI eval loop: incremental indexing, observability CLI, git context tools, and a contributor runbook.

### Added

- **Git-aware incremental index watch** — `annulus index watch`, gateway background watch option, standalone FTS5 schema with safe incremental deletes ([ADR-014](docs/architecture/adr-014-incremental-index-watch.md))
- **Trace CLI** — `annulus traces list`, `traces show`, `traces last` ([ADR-006](docs/architecture/adr-006-multi-client-architecture.md))
- **Git tools** — server-side `git_status` and `git_diff` ([ADR-015](docs/architecture/adr-015-local-swe-assistant-v04.md))
- **Eval runbook** — [v0.3 contributor checklist](.devcontainer/eval/README.md#v0.3-eval-runbook) with sample prompts and Continue setup
- **Continue ChatDescriber passthrough** — auto chat-title requests skip retrieval/tools; `traces last` skips title traces ([#45](https://github.com/johngrahamreynolds/annulus/issues/45))
- **ADR-016 (Proposed)** — TypeScript client-layer strategy (edge-only; engine stays Python)

### Changed

- Default local eval profiles shifted to **Gemma4** (`gemma4:12b` / `gemma4:26b`) with compatibility matrix ([ADR-013](docs/architecture/adr-013-model-tool-compatibility.md))
- Streaming tool loop with reasoning Thought UI (`delta.reasoning_content`) for capable profiles
- `<annulus_tools>` system prompt injection when Continue disables built-in tools
- Git incremental index skips unchanged paths via stored mtime ([#37](https://github.com/johngrahamreynolds/annulus/issues/37))

### Upgrade notes

If `.annulus/index.db` was created before v0.3, run **`annulus index --rebuild` once** per workspace after upgrading. See [README — Upgrading from older Annulus builds](README.md#upgrading-from-older-annulus-builds).

## [0.2.0]

Initial public eval release: FTS5 retrieval, server-side read/search tools, SQLite tracing, frontier escalation, eval devcontainer, Continue integration.
