# Status: Accepted

## Context

The MVP gateway passthrough proved Continue integration and local Ollama routing. The next step is to differentiate Annulus with repo-grounded answers and server-side tooling without breaking the OpenAI client contract.

## Decision

Add three packages and route all chat through `AgentRuntime`:

1. **`packages/retrieval`** — SQLite FTS5 index (`annulus index`) over workspace files
2. **`packages/tools`** — sandboxed `read_file`, `ripgrep`, `git_status`, and `git_diff` tools
3. **`packages/runtime`** — loop: retrieve → complete → execute tools → repeat

Retrieval runs **before** the first model call. Tools run **server-side** inside the gateway (clients do not need MCP for MVP).

Non-streaming responses include an `annulus` metadata block (escalation, retrieval hits, tools used). Streaming requests run the same tool loop when the profile has `supports_tools: true`; each turn uses Ollama streaming, forwarding content and reasoning deltas live on the final turn only. When `expose_reasoning: true`, Ollama `delta.reasoning` is forwarded as `delta.reasoning_content` for Continue's Thought UI instead of being folded into `delta.content`. Profiles without tool support still use retrieval-only passthrough streaming with the same normalization.

## Consequences

**Positive**

- Continue and CLI gain repo context without attaching full codebase
- Tool calls are traced and sandboxed to workspace root
- Clear extension point for GraphRAG and MCP later

**Negative**

- Tool-call turns buffer internally (no live forward once `tool_calls` deltas appear). Profiles with `expose_reasoning: true` emit `delta.reasoning_content` for Continue Thought UI; otherwise reasoning is mapped to `delta.content` for plain-text clients.
- FTS5 is lexical only (no embeddings yet)
- Index freshness depends on incremental `annulus index`, `annulus index watch`, or optional gateway background watch ([ADR-014](adr-014-incremental-index-watch.md)); full `--rebuild` after config changes or FTS schema upgrades

## References

- `packages/runtime/src/annulus_runtime/agent.py`
- `packages/retrieval/`
- `packages/tools/`
