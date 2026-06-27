# Status: Proposed

## Context

Full workspace index on a work repo (~280 files) took **~5 minutes**. Rebuilding the entire FTS5 index on every change is unacceptable for daily use. Contributors currently run `annulus index --rebuild` manually from the eval devcontainer.

Retrieval quality depends on reasonably fresh index state; users should not manage this explicitly in the target-native sidecar future ([ADR-012](adr-012-target-native-sidecar-deployment.md)).

## Decision

Add **incremental index watch** in v0.3 (`packages/retrieval` + CLI/gateway background task).

**Strategy (preferred): git-aware delta**

When `.git` exists in `ANNULUS_WORKSPACE_ROOT`:

1. Track last indexed commit (store in `.annulus/index_meta.json` or SQLite meta table).
2. On watch tick or gateway startup: `git diff --name-only <last_commit> HEAD` (+ untracked via `git status --porcelain` or `git ls-files -o --exclude-standard`).
3. **Re-index only** added/changed/deleted paths; remove chunks for deleted files.
4. Update stored commit SHA after successful incremental pass.

**Fallback (no git):** filesystem mtime scan with debounce — coarser, use for non-git workspaces.

**Operational modes:**

| Mode | Trigger |
|------|---------|
| `annulus index watch` | CLI long-running watch in devcontainer |
| Gateway background | Optional `agent.index_watch_enabled` for sidecar “just works” |

**Performance target:** incremental updates proportional to **changed files**, not total repo size. Full rebuild remains available (`annulus index --rebuild`) after model/chunk config changes.

**Not in v0.3 scope:** embedding re-index (v0.4); graph incremental update (v0.5).

## Consequences

**Positive**

- Large repos stay indexed without multi-minute rebuilds.
- Aligns with target-repo-only workflow; index lives in target `.annulus/`.

**Negative**

- Git-less repos get weaker incremental path.
- Renames, large merges, and `.gitignore` changes need careful handling; edge cases iteratively hardened.

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-012-target-native-sidecar-deployment.md](adr-012-target-native-sidecar-deployment.md)
- `packages/retrieval/`
