# Status: Accepted

## Context

Ollama should use host GPU/Metal. Annulus apps run in Docker or devcontainer with a bind-mounted workspace for v0.2 retrieval and tools.

## Decision

Run **Ollama on the host**; run Annulus in Docker or devcontainer. Containers use `OLLAMA_HOST=http://host.docker.internal:11434`.

- **Devcontainer**: single `dev` service; run `uv run annulus-gateway` inside it. Port 8080 forwarded to the host.
- **Production compose** (`docker/docker-compose.yml`): standalone `gateway` service with repo mounted read-only at `/workspace` and `ANNULUS_WORKSPACE_ROOT=/workspace`.
- **Images** install `ripgrep` so the server-side `ripgrep` tool works in containers.

## References

- `docker/docker-compose.yml`
- `docker/Dockerfile.dev`
- `docker/Dockerfile.gateway`
- `.devcontainer/`
