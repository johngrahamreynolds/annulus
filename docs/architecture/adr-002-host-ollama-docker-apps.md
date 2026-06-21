# Status: Accepted

## Context

Annulus targets local-first development on Apple Silicon with Ollama using Metal acceleration. Containerizing Ollama inside Docker on macOS forfeits GPU/Neural Engine access and complicates model cache management. Application services benefit from reproducible container environments.

## Decision

- Run **Ollama on the host** (default `http://127.0.0.1:11434`)
- Run **Annulus gateway and dev shell in Docker/devcontainer**
- Inside containers, set `OLLAMA_HOST=http://host.docker.internal:11434` with `extra_hosts: host-gateway`

The gateway performs **streaming passthrough** to Ollama's OpenAI-compatible `/v1/chat/completions` endpoint without transforming the stream in MVP.

## Consequences

**Positive**

- Best inference performance on M5 Max class hardware
- Reproducible Python environment in devcontainer
- Same gateway image deploys to cloud later; only `OLLAMA_HOST` changes

**Negative**

- Host must run Ollama separately (`ollama serve`)
- Linux cloud deployment may colocate Ollama or switch to API-only frontier routing

## References

- `docker/docker-compose.yml`
- `.devcontainer/docker-compose.dev.yml`
- `.env.example`
