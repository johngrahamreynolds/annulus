from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from annulus_core.config import AnnulusSettings


class ToolExecutor:
    def __init__(self, settings: AnnulusSettings) -> None:
        self.settings = settings
        self.root = settings.resolve_tools_root()

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "read_file":
            return self._read_file(arguments)
        if name == "ripgrep":
            return self._ripgrep(arguments)
        return json.dumps({"error": f"Unknown tool: {name}"})

    def _resolve_path(self, rel_path: str) -> Path:
        candidate = (self.root / rel_path).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError(f"Path escapes workspace sandbox: {rel_path}")
        return candidate

    def _read_file(self, arguments: dict[str, Any]) -> str:
        path = self._resolve_path(arguments["path"])
        if not path.exists() or not path.is_file():
            return json.dumps({"error": f"File not found: {arguments['path']}"})
        lines = path.read_text(encoding="utf-8").splitlines()
        start = int(arguments.get("start_line") or 1)
        end = int(arguments.get("end_line") or len(lines))
        start = max(1, start)
        end = min(len(lines), end)
        snippet = "\n".join(f"{i + 1}|{lines[i]}" for i in range(start - 1, end))
        return json.dumps({"path": arguments["path"], "content": snippet})

    def _ripgrep(self, arguments: dict[str, Any]) -> str:
        pattern = arguments["pattern"]
        rel_path = arguments.get("path", ".")
        max_results = int(arguments.get("max_results", 50))
        target = self._resolve_path(rel_path)
        cmd = [
            "rg",
            "--no-heading",
            "--line-number",
            "--color=never",
            "-m",
            str(max_results),
            pattern,
            str(target),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError:
            return json.dumps({"error": "ripgrep (rg) is not installed"})
        output = proc.stdout.strip() or proc.stderr.strip() or "(no matches)"
        return json.dumps({"pattern": pattern, "path": rel_path, "output": output[:8000]})
