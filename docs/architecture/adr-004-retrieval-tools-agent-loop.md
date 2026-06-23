# Status: Accepted

## Context

The MVP gateway passthrough proved Continue integration and local Ollama routing. The next step is to differentiate Annulus with repo-grounded answers and server-side tooling without breaking the OpenAI client contract.

## Decision

Add three packages and route all chat through `AgentRuntime`:

1. **`packages/retrieval`** — SQLite FTS5 index (`annulus index`) over workspace files
2. **`packages/tools`** — sandboxed `read_file` and `ripgrep` tools
3. **`packages/runtime`** — loop: retrieve → complete → execute tools → repeat

Retrieval runs **before** the first model call. Tools run **server-side** inside the gateway (clients do not need MCP for MVP).

Non-streaming responses include an `annulus` metadata block (escalation, retrieval hits, tools used). Streaming mode skips the tool loop for now and uses retrieval-only context injection before passthrough.

## Consequences

**Positive**

- Continue and CLI gain repo context without attaching full codebase
- Tool calls are traced and sandboxed to workspace root
- Clear extension point for GraphRAG and MCP later

**Negative**

- Streaming requests do not yet run the full tool loop
- FTS5 is lexical only (no embeddings yet)
- Index must be rebuilt manually (`annulus index`)

## References

- `packages/runtime/src/annulus_runtime/agent.py`
- `packages/retrieval/`
- `packages/tools/`
