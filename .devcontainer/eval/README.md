# External repo eval devcontainer

Annulus engine at `/workspace`; eval target mounted at `/target`.

## One-time setup

```bash
cp .devcontainer/eval/.env.example .devcontainer/eval/.env
```

Edit `.devcontainer/eval/.env` and set `ANNULUS_EVAL_REPO` to the **absolute host path** of the repo you are evaluating.

Add to that repo's `.gitignore` if missing:

```gitignore
.annulus/
```

**Why two env files?** Docker Compose resolves `${ANNULUS_EVAL_REPO}` in volume paths at build time from `.devcontainer/.env`. The eval devcontainer runs `pre-up.sh` before compose to copy your path from `eval/.env` into that file. Do not edit `.devcontainer/.env` by hand — it is gitignored and regenerated on each rebuild.

## Open

**Dev Containers: Reopen in Container** → **Annulus — External Repo Eval**  
(or **Open Container Configuration File…** → `.devcontainer/eval/devcontainer.json` → Rebuild)

Day-to-day dev uses `.devcontainer/default/devcontainer.json`.

## Verify

```bash
echo $ANNULUS_WORKSPACE_ROOT   # /target
ls /target
cd /workspace && uv run annulus index && uv run annulus-gateway
```

To eval a different repo, update `ANNULUS_EVAL_REPO` in `.devcontainer/eval/.env` and rebuild the container.
