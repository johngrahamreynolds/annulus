# Status: Proposed

## Context

Early development uses the **eval devcontainer**: Annulus engine at `/workspace`, target repo at `/target`, Continue in a **target-repo window** hitting `localhost:8080` ([`.devcontainer/eval/README.md`](../../.devcontainer/eval/README.md)). That is acceptable for contributors who understand the split.

**End users** should not need two repos, manual gateway commands, or compose internals. They open **their project** and get retrieval + agent tools with minimal setup.

## Decision

**Near term (v0.x contributors):** Keep eval devcontainer + Continue in target repo. Document `ANNULUS_EVAL_REPO` and rebuild flow.

**Medium term (end-user target):** **Target-native sidecar** — one simple configuration that points Annulus at the repo the user already has open.

```text
Today (dev):
  Window A: annulus repo → eval devcontainer → gateway
  Window B: target repo → Continue → localhost:8080

Target (end-user):
  Window: target repo only
    → sidecar starts gateway (compose or local process)
    → ANNULUS_WORKSPACE_ROOT = repo root
    → Continue / Annulus UI → localhost:8080
```

**Configuration surface (goal):** a single obvious setting, e.g.:

- Target repo `.annulus/config.yaml` or root `.env`:

  ```yaml
  # conceptual
  workspace: .
  gateway_port: 8080
  ```

- Or one line in existing env: `ANNULUS_WORKSPACE_ROOT=.` when gateway runs from a packaged sidecar.

Implementation options (TBD at build time):

| Approach | Notes |
|----------|--------|
| **Compose in target repo** | `docker compose up annulus` with published image; mount repo as workspace |
| **Host daemon** | `annulus serve` after `pip`/brew install; reads `.annulus/config.yaml` |
| **Devcontainer in target** | Target repo's `.devcontainer/` includes Annulus service (Annulus as image, not source checkout) |

Eval devcontainer in the Annulus monorepo remains the **dogfood path** for engine development; target-native sidecar is the **distribution path**.

**Index lifecycle:** Large work repos (~280 files, multi-minute full index) require **incremental index watch** ([ADR-014](adr-014-incremental-index-watch.md)), not full rebuild on every change. End users should not run `annulus index` manually after initial setup.

## Consequences

**Positive**

- Clear separation: contributor workflow vs product onboarding.
- Same engine (`AgentRuntime`, gateway) in both paths; only packaging differs.

**Negative**

- Two deployment stories to maintain until target-native path subsumes eval for most users.
- Published image / install story is additional release engineering (post–v0.3).

## References

- [vision.md](vision.md)
- [adr-002-host-ollama-docker-apps.md](adr-002-host-ollama-docker-apps.md)
- [adr-006-multi-client-architecture.md](adr-006-multi-client-architecture.md)
- `.devcontainer/eval/`
