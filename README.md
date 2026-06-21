# Annulus

Local-first, model-agnostic agentic AI platform. MVP gateway with OpenAI-compatible API, Ollama passthrough, and SQLite trace logging.

## Repo layout

```text
annulus/
├── apps/
│   ├── cli/                 # `annulus` CLI (chat, health)
│   └── gateway/             # FastAPI OpenAI-compatible gateway
├── packages/
│   ├── core/                # Config, types, settings
│   ├── router/              # Model router + Ollama client
│   └── trace/               # SQLite trace store
├── config/                  # YAML configuration
├── docker/                  # Dockerfiles and compose
├── docs/
│   ├── architecture/        # ADRs
│   └── continue-config.example.yaml
├── .devcontainer/           # VS Code / Cursor dev container
├── pyproject.toml           # uv workspace root
└── .env.example
```

## Prerequisites

Ollama must run on the **host** at port 11434 (`ollama serve`). Docker and dev-container workflows reach it via `host.docker.internal`; no change to `.env` is required for that — see [Ollama host URL](#ollama-host-url) below.

## Quick start (host)

Run directly on your machine with uv (Python 3.12+).

```bash
cp .env.example .env
uv sync
uv run annulus-gateway &
uv run annulus health
uv run annulus chat "Hello from Annulus"
```

## Quick start (dev container)

Open the repo in a dev container (`.devcontainer/devcontainer.json`, used by VS Code / Cursor). The container provides a Python environment and forwards port 8080, but **does not start the gateway automatically** — start it yourself, same as on the host.

```bash
cp .env.example .env   # if not already present
uv run annulus-gateway &
curl http://localhost:8080/health
uv run annulus health
uv run annulus chat "Hello from Annulus"
```

Use `localhost:8080` from inside the container. Do not use `host.docker.internal:8080` for the gateway; that address targets the host loopback, not the process in the container.

## Quick start (Docker — gateway only)

Runs the production-style gateway image via `docker/docker-compose.yml`. The gateway **starts automatically** on container launch.

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
curl http://localhost:8080/health
```

## Ollama host URL

| Where you run | `OLLAMA_HOST` |
|---|---|
| Host (uv on your machine) | `http://127.0.0.1:11434` (default in `.env.example`) |
| Dev container | Overridden to `http://host.docker.internal:11434` |
| Docker Compose (`docker/docker-compose.yml`) | Overridden to `http://host.docker.internal:11434` |

You only need to edit `.env` if you run the gateway outside these Docker overrides (for example, a plain `docker run` without the compose `environment:` block).

## Continue setup

Copy `docs/continue-config.example.yaml` into your Continue config and set the API key to match `.env`.

## Development

Use the [dev container](#quick-start-dev-container) for day-to-day work, or run `uv sync --group dev` on the host.

```bash
uv sync --group dev
uv run ruff check .
uv run pytest
```
