# Annulus

Local-first, model-agnostic agentic AI platform. The gateway exposes an OpenAI-compatible API with **retrieval-augmented** chat, a **server-side tool loop** (`read_file`, `ripgrep`), SQLite tracing, and **frontier escalation** when local models fail.

## Features (v0.2)

- **Retrieval** — FTS5 index over workspace code/docs (`annulus index`)
- **Agent loop** — server-side tool calling before responding
- **Tracing** — SQLite spans for chat, retrieval, tools, and iterations
- **Frontier escalation** — optional fallback to an OpenAI-compatible frontier API when local model errors or returns empty
- **Continue-ready** — OpenAI-compatible `/v1/chat/completions`

## Repo layout

```text
annulus/
├── apps/
│   ├── cli/                 # annulus health | index | chat
│   └── gateway/             # FastAPI gateway
├── packages/
│   ├── core/                # Config and shared types
│   ├── router/              # Ollama + OpenAI providers, escalation
│   ├── trace/               # SQLite trace store
│   ├── retrieval/           # Indexer + FTS retriever
│   ├── tools/               # read_file, ripgrep
│   └── runtime/             # Agent loop (retrieval → model → tools)
├── config/                  # YAML configuration
├── docker/
├── docs/
└── .devcontainer/
```

## Quick start

```bash
cp .env.example .env
uv sync --group dev

# 1. Index your workspace (required for retrieval)
uv run annulus index

# 2. Start gateway
uv run annulus-gateway

# 3. Verify
uv run annulus health
uv run annulus chat "Where is the agent loop implemented?" --no-stream
```

`annulus chat` **streams by default** (retrieval-augmented passthrough). Use **`--no-stream`** for the full agent loop: server-side tools and frontier escalation.

## Request flow

```text
Client (Continue / CLI)
  → POST /v1/chat/completions
  → AgentRuntime
      1. Retriever.search(user query) → inject context
      2. ModelRouter.complete (local Ollama)
      3. If tool_calls → ToolExecutor (read_file / ripgrep) → loop
      4. If local error/empty → escalate to frontier (OpenAI-compatible API)
  → TraceStore (SQLite spans — observability only, not chat memory)
  → Response (+ annulus metadata in non-streaming mode)
```

Steps 3–4 and escalation run only for **non-streaming** requests. Streaming requests get retrieval context injection, then a direct model passthrough.

## Streaming vs non-streaming

| Mode | Retrieval | Tool loop | Frontier escalation |
|------|-----------|-----------|---------------------|
| **Streaming** (`stream: true`, CLI default) | Yes | No | No |
| **Non-streaming** (`--no-stream`) | Yes | Yes | Yes |

Continue and other clients that stream behave like the first row unless you disable streaming in the client.

## Stateless gateway

Annulus does **not** persist chat history on the server. Each request uses the `messages` array the client sends. SQLite traces (`.annulus/traces.db`) log spans for debugging and evals — they are **not** replayed into future prompts. Cross-turn context is the client's responsibility (e.g. Continue thread history).

## Configuration

| Source | Purpose |
|--------|---------|
| `.env` | API keys, paths, Ollama host, escalation toggle, frontier base URL |
| `config/default.yaml` | Agent, retrieval, tools settings |
| `config/models.yaml` | Model profiles and escalation rules |

Set `OPENAI_API_KEY` to enable frontier escalation. Point `OPENAI_BASE_URL` at an OpenAI-compatible endpoint (OpenAI, LiteLLM ZDR, etc.). Without a key, `/health` reports `frontier: missing_api_key` and escalation attempts will fail.

Configure the frontier model name in `config/models.yaml` under the `frontier` profile.

## Continue

See `docs/continue-config.example.yaml`. Point `apiBase` at `http://localhost:8080/v1`.

## Docker / devcontainer

Ollama runs on the **host**. Containers reach it via `host.docker.internal:11434`.

**Production-style gateway** (standalone container):

```bash
docker compose -f docker/docker-compose.yml up --build
```

The gateway container bind-mounts the repo read-only at `/workspace` for indexing and tool sandbox paths. Set `ANNULUS_WORKSPACE_ROOT=/workspace` (already in compose).

**Devcontainer** (`.devcontainer/`): opens a `dev` service with the repo at `/workspace`. After `uv sync --group dev`:

```bash
uv run annulus index
uv run annulus-gateway
```

Run the gateway as a process inside `dev`; port 8080 is forwarded to the host for Continue and `annulus health`. Images include `ripgrep` for the agent `ripgrep` tool.

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run pytest
```

## Data files

| Path | Contents |
|------|----------|
| `.annulus/traces.db` | Request/tool/retrieval spans |
| `.annulus/index.db` | FTS5 code/doc index |

Both are gitignored and persist on the bind-mounted workspace in devcontainer.
