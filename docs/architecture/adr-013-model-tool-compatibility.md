# Status: Proposed

## Context

Tool calling quality is **model- and provider-specific**. Early eval (v0.2) used **llama3.1:8b** as the default local profile. v0.3 eval on Apple Silicon + Continue shifted defaults to the **Gemma4** family.

Annulus gates tools with `profile.supports_tools` and only executes `message.tool_calls` ([ADR-004](adr-004-retrieval-tools-agent-loop.md)). There is no content-JSON fallback yet and no per-profile reasoning-channel handling.

## Compatibility matrix (v0.3 eval)

Hand-maintained from Continue eval and `scripts/probe_ollama_tools.py`. Re-run probes after Ollama or model tag updates.

| Profile | Ollama model | `supports_tools` | Native `tool_calls` | Streaming tools | Eval notes |
|---------|--------------|------------------|---------------------|-----------------|------------|
| **local** | `gemma4:12b` | yes | yes | yes | **Primary default.** Reliable tool loop; good tool choice (e.g. ripgrep vs read_file). |
| **local-large** | `gemma4:26b` | yes | yes | yes | **Large local tier.** Probe ✅; agent loop ✅ (e.g. 2 iter, 1× ripgrep). Occasional conflicting “no tools provided” text in Continue (see open questions). |
| **gpt-oss** | `gpt-oss:20b` | yes | yes | yes | **Experimental / opt-in.** Probe ✅; agent loop ✅ (may duplicate ripgrep). Instruction-conflict in some Continue threads. |
| **local-coder** | `qwen2.5-coder:…` | no | no | passthrough only | Tool intent in `content` as JSON, not `tool_calls` — chat/retrieval only unless fallback is built. |
| **frontier** | OpenAI-compatible | yes | yes | yes | Escalation target; requires `OPENAI_API_KEY`. |
| *(historical)* | `llama3.1:8b` | yes | yes | yes | Previous default; reliable native `tool_calls` in v0.2 eval. |

**Probe script:**

```bash
# Host: Ollama on 127.0.0.1. Devcontainer: set OLLAMA_HOST or pass --base.
python scripts/probe_ollama_tools.py gemma4:12b --full-tools
python scripts/probe_ollama_tools.py gemma4:12b --full-tools --base http://host.docker.internal:11434
```

Reports `tool_calls` vs content-JSON vs error for stream and non-stream against Ollama directly (bypasses Annulus agent loop and any mounted workspace). The default prompt mentions TODO only as a fixed ripgrep pattern — not your indexed repo.

Probe verified stream + non-stream native `tool_calls` for gemma4:12b, gemma4:26b, and gpt-oss:20b (v0.3 eval, Jun 2026). `annulus chat --no-stream` on a mounted target repo confirmed the full agent loop for `local-large` (2 iterations, 1× ripgrep) and `gpt-oss` (3 iterations, 2× ripgrep).

## Decision

Introduce a **model tool compatibility** layer (v0.3), separate from the `supports_tools` boolean.

**Capability dimensions (extend `ModelProfile` / `models.yaml` — future):**

| Capability | Meaning | Annulus behavior |
|------------|---------|------------------|
| `supports_tools` | Model may receive tool schemas | Attach `tools` / `tool_choice` to payload |
| `native_tool_calls` | Provider returns OpenAI-shaped `tool_calls` | Execute from `message.tool_calls` (default when supports_tools) |
| `parallel_tool_calls` | Multiple tools in one assistant message | If false, expect at most one tool call per turn (gpt-oss-style) |
| `content_tool_fallback` | Model emits `{"name", "arguments"}` in `content` | Optional parse-and-execute fallback (qwen-style); off by default |
| `expose_reasoning` | Stream reasoning separately for clients | Emit `reasoning_content` deltas for Continue Thought UI (not implemented) |

**Profile tier defaults (`config/models.yaml`):**

- **`local`** → `gemma4:12b` — daily driver and default `chat` profile.
- **`local-large`** → `gemma4:26b` — larger local MoE tier.
- **`gpt-oss`** → opt-in comparison profile, not the large default.

**v0.3 deliverables:**

1. **`scripts/probe_ollama_tools.py`** — probe stream + non-stream tool calling (done).
2. **Compatibility table** in this ADR (done; maintain from eval).
3. **`annulus models probe-tools`** — optional CLI wrapper (not done).
4. **Runtime:** normalize tool call extraction (partially done via streaming helpers).
5. **Traces:** record `tool_extraction: native | fallback | none` on agent iterations (not done).

**Sequential vs parallel:** `AgentRuntime` already executes multiple `tool_calls` entries in order in one iteration. Models that emit one tool call per turn fit naturally.

## Consequences

**Positive**

- Gemma4 defaults documented; gpt-oss kept for comparison without blocking the happy path.
- Probe script gives a repeatable check before changing profiles.

**Negative**

- Matrix is hand-maintained until probe automation lands.
- Instruction-conflict failures are not solved by profile naming alone.

## Open questions

- **Conflicting tool instructions:** Models sometimes quote text like *“THE USER HAS NOT PROVIDED ANY TOOLS…”* on Gemma4 26B and gpt-oss — likely Continue/system prompt vs API `tools` mismatch; track as a separate issue.
- **Reasoning presentation:** Continue Thought UI vs Annulus `reasoning` → `content` remap — track separately.
- Ollama-specific fields (`tool_name` on tool role messages, missing `id`) — normalize in router or runtime?
- When to escalate on tool-format failure vs retry with stripped tools?

## References

- [vision.md](vision.md)
- [adr-004-retrieval-tools-agent-loop.md](adr-004-retrieval-tools-agent-loop.md)
- [adr-011-governed-self-improvement.md](adr-011-governed-self-improvement.md)
- `scripts/probe_ollama_tools.py`
- `config/models.yaml`
- `packages/runtime/src/annulus_runtime/agent.py`
