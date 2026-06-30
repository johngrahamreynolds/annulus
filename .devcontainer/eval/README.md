# External repo eval devcontainer

Annulus engine at `/workspace`; eval target mounted at `/target`.

## One-time setup

```bash
cp .devcontainer/eval/.env.example .devcontainer/eval/.env
```

Edit `.devcontainer/eval/.env` and set `ANNULUS_EVAL_REPO` to the **absolute host path** of the repo you are evaluating.

| Platform | Example |
|----------|---------|
| macOS | `/Users/you/projects/my-repo` |
| Linux | `/home/you/projects/my-repo` |
| Windows | `C:\Users\you\projects\my-repo` |

Add to that repo's `.gitignore` if missing:

```gitignore
.annulus/
```

**Why two env files?** Docker Compose resolves `${ANNULUS_EVAL_REPO}` in volume paths at build time from `.devcontainer/.env`. The eval devcontainer runs `pre-up.sh` before compose to copy your path from `eval/.env` into that file. Do not edit `.devcontainer/.env` by hand — it is gitignored and regenerated on each rebuild.

**Line endings:** Shell scripts use LF (see repo root `.gitattributes`). If `pre-up.sh` fails on Windows with `$'\r': command not found`, re-checkout the file or run `git add --renormalize .`.

## Open

**Dev Containers: Reopen in Container** → **Annulus — External Repo Eval**  
(or **Open Container Configuration File…** → `.devcontainer/eval/devcontainer.json` → Rebuild)

Day-to-day dev uses `.devcontainer/default/devcontainer.json`.

## Verify

```bash
echo $ANNULUS_WORKSPACE_ROOT   # /target
ls /target
cd /workspace && uv sync --group dev && uv run annulus index && uv run annulus-gateway
```

In another terminal inside the container (or background the gateway):

```bash
uv run annulus health
```

Expect `ollama: ok` and `ollama_openai_compat: ok` (or check JSON with `--json`).

## Troubleshooting (Windows)

### `404 Not Found` for `http://host.docker.internal:11434/v1/chat/completions`

Annulus talks to **Ollama on the host** via `OLLAMA_HOST` (see `docker-compose.dev.yml`). The gateway and CLI use `/v1/chat/completions`; a 404 usually means:

1. **Ollama is too old** — upgrade to a current [Ollama](https://ollama.com) release with OpenAI-compatible API support.
2. **Ollama is not running** on the Windows host — start the Ollama app; confirm `http://127.0.0.1:11434` works in a host browser or `curl http://127.0.0.1:11434/api/tags`.
3. **Wrong service on port 11434** — nothing else should bind that port.

From inside the container:

```bash
curl -s http://host.docker.internal:11434/api/tags
curl -s http://host.docker.internal:11434/v1/models
uv run annulus health --json
```

If `/api/tags` works but `/v1/models` returns 404, upgrade Ollama.

### Continue / IDE

Point Continue at the **Annulus gateway**, not Ollama directly:

```yaml
apiBase: http://localhost:8080/v1
model: local
```

Port `8080` is forwarded from the devcontainer. Do not set `apiBase` to `http://host.docker.internal:11434/v1`.

### Eval mount path

Use a **Windows-native** path in `eval/.env` (`C:\Users\...`). Docker validates the bind mount; `pre-up.sh` does not rewrite paths across platforms.

To eval a different repo, update `ANNULUS_EVAL_REPO` in `.devcontainer/eval/.env` and rebuild the container.
