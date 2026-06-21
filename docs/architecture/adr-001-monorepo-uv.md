# Status: Accepted

## Context

Annulus will grow into multiple Python packages (runtime, retrieval, memory, tools) and applications (gateway, CLI, indexer). We need reproducible dependency management, fast installs on a developer laptop, and a layout that supports shared libraries without premature microservice extraction.

## Decision

Use a **uv workspace monorepo** with:

- Root `pyproject.toml` declaring workspace members under `packages/*` and `apps/*`
- One committed `uv.lock` for reproducible Docker and devcontainer builds
- `src/` layout per package (`annulus_core`, `annulus_router`, etc.)
- Shared dev tooling (ruff, pytest) at the workspace root

Poetry and plain `requirements.txt` were considered. Poetry adds slower resolves; `requirements.txt` does not scale to multi-package workspaces.

## Consequences

**Positive**

- Fast `uv sync` on M-series hardware; single venv for local dev
- Workspace members resolve each other without publishing to PyPI
- Docker/devcontainer can `uv sync --frozen --package annulus-gateway` for minimal prod images

**Negative**

- Contributors must install `uv` (acceptable for this project)
- Hatch build config per package must stay consistent

## References

- Root `pyproject.toml`
- `uv.lock`
