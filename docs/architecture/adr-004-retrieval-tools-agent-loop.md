# Status: Accepted

## Context

The MVP gateway passthrough proved Continue integration and local Ollama routing. The next step is to differentiate Annulus with repo-grounded answers and server-side tooling without breaking the OpenAI client contract.

## Decision

Add three packages and route all chat through `AgentRuntime`:

1. **`packages/retrieval`** — SQLite FTS5 index (`annulus index`) over workspace files
2. **`packages/tools`** — sandboxed `read_file` and `ripgrep` tools
3. **`packages/runtime`** — loop: retrieve → complete → execute tools → repeat

Retrieval runs **before** the first model call. Tools run **server-side** inside the gateway (clients do not need MCP for MVP).

Non-streaming responses include an `annulus` metadata block (escalation, retrieval hits, tools used). Streaming requests run the same tool loop when the profile has `supports_tools: true`; each turn uses Ollama streaming, forwarding content/reasoning deltas live on the final turn only. Profiles without tool support still use retrieval-only passthrough streaming.

## Consequences

**Positive**

- Continue and CLI gain repo context without attaching full codebase
- Tool calls are traced and sandboxed to workspace root
- Clear extension point for GraphRAG and MCP later

**Negative**

- Tool-call turns buffer internally (no live forward once `tool_calls` deltas appear); reasoning is mapped to `content` for CLI compatibility — native `reasoning_content` for Continue is a follow-up
- FTS5 is lexical only (no embeddings yet)
- Index must be rebuilt manually (`annulus index`)

## References

- `packages/runtime/src/annulus_runtime/agent.py`
- `packages/retrieval/`
- `packages/tools/`
