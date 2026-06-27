# Status: Proposed

## Context

Tool calling quality is **model- and provider-specific**. v0.2 eval showed:

- **llama3.1:8b** (Ollama): native `message.tool_calls`, works with `AgentRuntime`.
- **qwen2.5-coder**: tool intent in `content` as JSON text, not `tool_calls` — loop exits after one iteration.
- **gpt-oss:20b** (reported): capable tool caller with **sequential-only** tool use (no parallel tool calls in one response); may still fail if Ollama returns non-standard message shapes.

Annulus today gates tools with `profile.supports_tools` and only executes `message.tool_calls` ([ADR-004](adr-004-retrieval-tools-agent-loop.md)). There is no model capability matrix, no content-JSON fallback, and no handling for provider-specific tool metadata.

## Decision

Introduce a **model tool compatibility** layer (v0.3), separate from “supports tools” boolean.

**Capability dimensions (extend `ModelProfile` / `models.yaml`):**

| Capability | Meaning | Annulus behavior |
|------------|---------|------------------|
| `supports_tools` | Model may receive tool schemas | Attach `tools` / `tool_choice` to payload |
| `native_tool_calls` | Provider returns OpenAI-shaped `tool_calls` | Execute from `message.tool_calls` (default when supports_tools) |
| `parallel_tool_calls` | Multiple tools in one assistant message | If false, execute tool_calls **sequentially** in one iteration (already how `AgentRuntime` loops); do not expect parallel requests from model |
| `content_tool_fallback` | Model emits `{"name", "arguments"}` in `content` | Optional parse-and-execute fallback (qwen-style); off by default per profile |

**gpt-oss:20b (working hypothesis):**

- Treat as tool-capable with `parallel_tool_calls: false`.
- Failures in eval likely due to **response shape** (Ollama/OpenAI-compat), missing fields, or escalation misfires — not inherent inability to tool. Debug with probe CLI before marking profile unsupported.

**v0.3 deliverables:**

1. **`annulus models probe-tools`** (or similar) — send minimal tool schema to profile's backend; report `tool_calls` vs content-JSON vs error.
2. **Documented compatibility table** in repo (generated or hand-maintained from probes).
3. **Runtime:** normalize tool call extraction (single function used by streaming and non-streaming loops).
4. **Traces:** record `tool_extraction: native | fallback | none` on agent iterations for eval.

**Sequential vs parallel:** Current loop already runs multiple `tool_calls` entries in order in one iteration, then continues to the next model turn. Models that emit **at most one** tool call per turn (gpt-oss) fit naturally; no parallel fan-out required in v0.3.

**Improvement over time ([ADR-011](adr-011-governed-self-improvement.md)):** Eval traces and probe results feed Loop B (routing / profile defaults) — not autonomous code changes.

## Consequences

**Positive**

- gpt-oss and future models debugged systematically, not ad hoc.
- Clear path for qwen as chat-only (`supports_tools: false`) vs optional fallback.

**Negative**

- Fallback parsing is brittle; prefer native `tool_calls` where possible.
- Matrix maintenance burden until probe automation exists.

## Open questions

- Ollama-specific fields (`tool_name` on tool role messages, missing `id`) — normalize in router or runtime?
- When to escalate on tool-format failure vs retry with stripped tools?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-011-governed-self-improvement.md](adr-011-governed-self-improvement.md)
- `packages/runtime/src/annulus_runtime/agent.py`
- `config/models.yaml`
