# Status: Proposed

## Context

Hybrid FTS + embeddings ([ADR-009](adr-009-hybrid-retrieval-embeddings.md)) improves **recall** but not **structure**: questions like "what imports this module?", "how does experiment A relate to script B?", or "trace the data flow from config to output" need **relationships**, not just similar text.

GraphRAG — retrieval augmented by a **knowledge graph** over entities and edges — is a proven pattern for multi-hop search. The maintainer's professional agent-swarm search work integrates GraphRAG; Annulus should adopt a **GraphRAG-lite** scope appropriate to a workspace sidecar (not a enterprise search product).

## Decision

Add a **workspace-scoped graph layer** in `packages/retrieval` (target **v0.5**), built at index time and queried at retrieval time.

**Index time — extract and store:**

| Node types | Edge types (examples) |
|------------|------------------------|
| Files, symbols (defs), headings | `imports`, `references`, `contains` |
| Config keys, doc sections | `documents`, `calls` (best-effort) |

- Store nodes/edges in SQLite alongside FTS and embedding tables (same `index.db` or namespaced schema).
- Extraction: tree-sitter or lightweight static analysis for Python/code; markdown structure for docs; extensible for notebooks and bib files in research repos.

**Query time — GraphRAG-lite:**

```text
query → FTS + vector seed chunks
     → expand 1–2 hops on graph (neighbors, importers, linked docs)
     → merge · rank · truncate → context block
```

- Hop limit and edge-type filters are configurable (`retrieval.graph.max_hops`, allowlist).
- Trace spans record seed hits, expanded nodes, and edges used.

**Scope discipline (lite):**

- No distributed graph DB; no cross-workspace federation in v0.5.
- Best-effort edges OK; precision improves iteratively.
- Full swarm orchestration consumes graph via same retriever ([ADR-008](adr-008-agent-swarm-orchestration.md)).

**UI hook ([ADR-006](adr-006-multi-client-architecture.md)):**

- Graph subset renderable in future Annulus UI side panel; CLI may dump `annulus index --graph-stats`.

## Consequences

**Positive**

- Answers structural and cross-file research questions FTS/embeddings miss alone.
- Aligns Annulus with agent-swarm + GraphRAG patterns used in related work.
- Clear upgrade path from v0.2 FTS-only eval learnings.

**Negative**

- Index complexity and build time increase.
- Static analysis is language-specific; imperfect graphs can mislead — trace metadata and eval prompts essential.

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-009-hybrid-retrieval-embeddings.md](adr-009-hybrid-retrieval-embeddings.md)
- `packages/retrieval/`
