# Status: Proposed

## Context

v0.2 retrieval is **FTS5 lexical search** over workspace chunks ([ADR-004](adr-004-retrieval-tools-agent-loop.md)). That works well when queries share vocabulary with the codebase (file names, symbols, README wording). It fails on **semantic** queries — concepts described differently, cross-domain language, "find the part that handles X" when X is never named in text.

Embeddings are the standard complement to lexical search. Annulus should add them **without replacing** FTS5 or breaking the sidecar index model.

## Decision

Add **hybrid retrieval** in `packages/retrieval` (target **v0.4**):

```text
user query
    ├── FTS5 search  ──┐
    │                  ├── merge · dedupe · rerank → context block
    └── vector search ─┘
```

**Storage:**

- Extend workspace `index.db` (or documented sidecar schema) with embedding tables.
- Prefer sqlite-vec or equivalent embeddable store; avoid mandatory external vector DB for local-first default.

**Indexing:**

- `annulus index` embeds chunks at index time using a configured **embed** profile in `models.yaml`.
- Reuse chunk boundaries from v0.2; improve with AST-aware splits for code in a follow-up.

**Configuration (`config/default.yaml` / `models.yaml`):**

```yaml
retrieval:
  mode: hybrid          # fts | embed | hybrid
  top_k: 5
  hybrid:
    fts_weight: 0.5
    embed_weight: 0.5
    rerank: false       # optional rerank profile later
```

**Runtime:**

- `Retriever.search()` returns merged ranked chunks; `AgentRuntime` injection unchanged ([ADR-004](adr-004-retrieval-tools-agent-loop.md)).
- Trace spans record FTS hits, embed hits, and final selection.

**Embed model options:**

- Local Ollama embedding model on laptop ([ADR-002](adr-002-host-ollama-docker-apps.md)).
- Remote embed endpoint via profile `apiBase` ([ADR-007](adr-007-remote-compute-profiles.md)).

## Consequences

**Positive**

- Better recall on large scientific and engineering repos.
- FTS remains fast and exact for symbol/path-like queries.
- Foundation for GraphRAG seed selection ([ADR-010](adr-010-graphrag-lite.md)).

**Negative**

- Index time and disk size increase; reindex required when embed model changes.
- Another model dependency to configure and health-check.

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-007-remote-compute-profiles.md](adr-007-remote-compute-profiles.md)
- `packages/retrieval/`
