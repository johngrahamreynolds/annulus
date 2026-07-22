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

## v0.3 eval runbook

Single path for contributors: **index → health → chat → traces → Continue**. Each sample prompt below works in a **fresh thread** (no prior chat history required).

**Default eval model:** profile **`local`** → **`gemma4:12b`** on host Ollama ([ADR-013 compatibility matrix](../../docs/architecture/adr-013-model-tool-compatibility.md)). Pull before first eval:

```bash
ollama pull gemma4:12b
```

**Large local tier (recommended if your machine has enough RAM/VRAM):** profile **`local-large`** → **`gemma4:26b`**. Same tool loop and Continue setup; select **Annulus Local Large** in Continue or pass `--model local-large` to the CLI. Useful for heavier reasoning and longer tool loops during eval.

```bash
ollama pull gemma4:26b
```

| Profile | Continue model name | Ollama tag | When to use |
|---------|---------------------|------------|-------------|
| **`local`** | Annulus Local | `gemma4:12b` | Default daily eval; fits most laptops |
| **`local-large`** | Annulus Local Large | `gemma4:26b` | Deeper reasoning / complex tool plans if Ollama runs acceptably on your hardware |
| **`gpt-oss`** | Annulus GPT-OSS | `gpt-oss:20b` | Experimental comparison only ([ADR-013](../../docs/architecture/adr-013-model-tool-compatibility.md)) |

Probe either tier before a eval session:

```bash
cd /workspace && uv run python scripts/probe_ollama_tools.py gemma4:12b --full-tools \
  --base http://host.docker.internal:11434
uv run python scripts/probe_ollama_tools.py gemma4:26b --full-tools \
  --base http://host.docker.internal:11434
```

### Contributor checklist

Complete in order inside the eval devcontainer (with Ollama running on the **host**).

| Step | Action | Pass criteria |
|------|--------|---------------|
| 1 | `echo $ANNULUS_WORKSPACE_ROOT` | Prints `/target`; `ls /target` shows your repo |
| 2 | `cd /workspace && uv sync --group dev` | Dependencies installed |
| 3 | `annulus index --rebuild` | Index built under `/target/.annulus/` (once per repo or after Annulus upgrade — see [Upgrading](#upgrading-annulus-existing-eval-workspaces)) |
| 4 | Start **`annulus-gateway`** (terminal 1) | Listening on port 8080 |
| 5 | Start **`annulus index watch`** (terminal 2, optional) | Keeps index fresh while you edit `/target` |
| 6 | **`annulus health`** | `ollama: ok`, `ollama_openai_compat: ok`, index file/chunk counts > 0 |
| 7 | **Continue** in the devcontainer (or CLI below) | See [Continue setup](#continue-setup) |
| 8 | Run a [sample prompt](#sample-prompts) | Sensible answer; for tool prompts, see step 9 |
| 9 | **`annulus traces last`** | Spans include `retrieval.search` and/or `tool.*` as expected |

**CLI-only smoke (steps 7–9 without Continue):**

```bash
annulus chat "Use ripgrep to find AgentRuntime in packages/runtime" --no-stream
annulus traces last

# optional — same prompt on the large local tier
annulus chat "Use ripgrep to find AgentRuntime in packages/runtime" --no-stream --model local-large
annulus traces last
```

**References:** [`docs/continue-config.example.yaml`](../../docs/continue-config.example.yaml) · [ADR-013 model matrix](../../docs/architecture/adr-013-model-tool-compatibility.md) · `scripts/probe_ollama_tools.py`

### Terminal layout

```text
Terminal 1   annulus-gateway
Terminal 2   annulus index watch          # optional; skip if you run annulus index after edits
Terminal 3   annulus health | chat | traces last
```

With `(annulus)` venv active you can omit `uv run` (same commands).

### Continue setup

1. Copy [`docs/continue-config.example.yaml`](../../docs/continue-config.example.yaml) into your Continue config (user or workspace).
2. Select **Annulus Local** (`local` → `gemma4:12b`) or **Annulus Local Large** (`local-large` → `gemma4:26b`) if you pulled the 26B model.
3. Confirm **`apiBase: http://localhost:8080/v1`** and **`apiKey: dev-local-key`** — the Annulus gateway, **not** Ollama directly.
4. **Disable Continue built-in tools** (Tool Policies / tool settings). Annulus runs **server-side** tools (`read_file`, `ripgrep`, `git_status`, `git_diff`). Built-in IDE tools conflict with Annulus tool calling ([ADR-013](../../docs/architecture/adr-013-model-tool-compatibility.md#open-questions)).
5. Open a **new Continue chat** for each sample prompt below (clean thread, no history).

Port `8080` is forwarded from the devcontainer to the host.

### Sample prompts

Use profile **`local`** (12B) by default, or **`local-large`** (26B) for heavier eval — both support the full server-side tool loop per [ADR-013](../../docs/architecture/adr-013-model-tool-compatibility.md).

| Goal | Prompt | Expect in `annulus traces last` |
|------|--------|----------------------------------|
| **Retrieval** | Where is the agent loop implemented in this repo? | `retrieval.search` with hits > 0; answer cites real paths |
| **Tool — ripgrep** | Use ripgrep to find where `AgentRuntime` is defined under `packages/runtime`. Call the tool before answering. | `tool.ripgrep`; often 2× `agent.iteration` |
| **Tool — read_file** | Read `packages/runtime/src/annulus_runtime/agent.py` and summarize the tool loop in three sentences. | `tool.read_file` |
| **Git context** | What files have I changed? Use git_status first, then summarize. | `tool.git_status` (and optionally `tool.git_diff`) |
| **Multi-turn** (same thread) | **Turn 1:** Use ripgrep to find the Indexer class in `packages/retrieval`. **Turn 2:** Read its `index_incremental` method and explain git vs mtime strategy. | Turn 1: `tool.ripgrep`; Turn 2: `tool.read_file` or retrieval |

After any tool-heavy prompt, run **`annulus traces last`** and confirm span names, iteration count, and retrieval hits. Use **`annulus traces list`** for history.

**Traces:** v0.3 shows a **flat timeline** (not nested parents yet). Trace id matches HTTP header `X-Annulus-Trace-Id` but is not shown in the chat UI — use `traces last` after Continue sessions.

### Indexing (day to day)

```bash
annulus index watch
```

Or one-shot after edits: `annulus index` (incremental by default). Use `annulus index --rebuild` after chunk config changes or Annulus upgrades.

Optional gateway background watch: set `agent.index_watch_enabled: true` in `config/default.yaml`.

## Upgrading Annulus (existing eval workspaces)

If `/target/.annulus/index.db` was created before v0.3 incremental watch, run a **one-time rebuild** after pulling Annulus:

```bash
uv run annulus index --rebuild
```

v0.3 uses a new FTS5 schema (required for safe incremental deletes). The store migrates the FTS table on open, but rebuild ensures chunks and search stay in sync. Symptoms of a stale index: empty retrieval, `database disk image is malformed`, or `table chunks_fts has no column named chunk_id` — all fixed by `--rebuild` (or delete `/target/.annulus/` and rebuild).

Default `annulus index` (no flags) is **incremental**, not a full rebuild.

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

### Model missing or slow first response

```bash
ollama pull gemma4:12b
ollama pull gemma4:26b    # if using local-large
ollama list
```

Confirm the tag you use (`gemma4:12b` or `gemma4:26b`) appears before eval. Re-run probes from [ADR-013](../../docs/architecture/adr-013-model-tool-compatibility.md):

```bash
cd /workspace && uv run python scripts/probe_ollama_tools.py gemma4:12b --full-tools \
  --base http://host.docker.internal:11434
uv run python scripts/probe_ollama_tools.py gemma4:26b --full-tools \
  --base http://host.docker.internal:11434
```

### Continue / IDE

Point Continue at the **Annulus gateway**, not Ollama directly:

```yaml
apiBase: http://localhost:8080/v1
model: local          # gemma4:12b — default
# model: local-large  # gemma4:26b — if pulled and your machine can run it
```

Port `8080` is forwarded from the devcontainer. Do not set `apiBase` to `http://host.docker.internal:11434/v1`.

Disable **Continue built-in tools** (Tool Policies). See [Continue setup](#continue-setup) and [`docs/continue-config.example.yaml`](../../docs/continue-config.example.yaml).

### Eval mount path

Use a **Windows-native** path in `eval/.env` (`C:\Users\...`). Docker validates the bind mount; `pre-up.sh` does not rewrite paths across platforms.

To eval a different repo, update `ANNULUS_EVAL_REPO` in `.devcontainer/eval/.env` and rebuild the container.
