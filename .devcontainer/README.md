# Dev Containers

Two configurations live in **subfolders** so Cursor / VS Code can offer a picker (a root `.devcontainer/devcontainer.json` hides alternatives).

| Folder | Use |
|--------|-----|
| **`default/`** | Day-to-day Annulus development (`/workspace` = this repo) |
| **`eval/`** | External repo eval (`/target` = mounted project) — see [eval/README.md](eval/README.md) |

## Open a configuration

1. **Command Palette** → **`Dev Containers: Reopen in Container`**  
   You should see **Annulus** and **Annulus — External Repo Eval**. Pick one.

2. If no picker appears: **`Dev Containers: Open Container Configuration File…`** → choose  
   `.devcontainer/default/devcontainer.json` or `.devcontainer/eval/devcontainer.json` → **Rebuild Container**.

3. After the default container is running: **`Dev Containers: Switch Container…`** to change to eval (or back).
