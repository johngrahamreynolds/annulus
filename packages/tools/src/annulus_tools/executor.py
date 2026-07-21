from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from annulus_core.config import AnnulusSettings

from annulus_tools.git_tools import git_available, run_git, truncate_output


class ToolExecutor:
    def __init__(self, settings: AnnulusSettings) -> None:
        self.settings = settings
        self.root = settings.resolve_tools_root()

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "read_file":
            return self._read_file(arguments)
        if name == "ripgrep":
            return self._ripgrep(arguments)
        if name == "git_status":
            return self._git_status()
        if name == "git_diff":
            return self._git_diff(arguments)
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
        rel_path = self._normalize_rel_path(arguments.get("path", "."))
        max_results = self._coerce_max_results(arguments.get("max_results"))
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
        if proc.returncode not in (0, 1):
            output = (
                proc.stderr.strip()
                or proc.stdout.strip()
                or f"rg exited with code {proc.returncode}"
            )
        else:
            output = proc.stdout.strip() or "(no matches)"
        return json.dumps({"pattern": pattern, "path": rel_path, "output": output[:8000]})

    def _git_status(self) -> str:
        if not git_available(self.root):
            return json.dumps({"error": "Not a git repository"})
        branch_code, branch_out, branch_err = run_git(self.root, "branch", "--show-current")
        status_code, status_out, status_err = run_git(
            self.root,
            "status",
            "--porcelain=v1",
            "-b",
        )
        if branch_code not in (0,) and status_code not in (0,):
            detail = (branch_err or status_err or "git status failed").strip()
            return json.dumps({"error": detail})
        branch = branch_out.strip() or "(detached)"
        status_text, truncated = truncate_output(status_out.strip() or "(clean)")
        payload: dict[str, Any] = {"branch": branch, "status": status_text}
        if truncated:
            payload["truncated"] = True
        return json.dumps(payload)

    def _git_diff(self, arguments: dict[str, Any]) -> str:
        if not git_available(self.root):
            return json.dumps({"error": "Not a git repository"})
        staged = bool(arguments.get("staged"))
        cmd: list[str] = ["diff"]
        if staged:
            cmd.append("--staged")
        rel_path = arguments.get("path")
        if rel_path:
            resolved = self._resolve_path(self._normalize_rel_path(rel_path))
            if not resolved.exists():
                return json.dumps({"error": f"Path not found: {rel_path}"})
            rel = (
                "."
                if resolved == self.root
                else str(resolved.relative_to(self.root))
            )
            cmd.extend(["--", rel])
        code, stdout, stderr = run_git(self.root, *cmd, timeout=60)
        if code not in (0, 1):
            detail = (stderr or stdout or f"git diff exited with code {code}").strip()
            return json.dumps({"error": detail})
        diff_text, truncated = truncate_output(stdout.strip() or "(no diff)")
        payload: dict[str, Any] = {
            "staged": staged,
            "path": rel_path or ".",
            "diff": diff_text,
        }
        if truncated:
            payload["truncated"] = True
        return json.dumps(payload)

    @staticmethod
    def _normalize_rel_path(value: Any) -> str:
        if value is None:
            return "."
        text = str(value).strip()
        return text or "."

    @staticmethod
    def _coerce_max_results(value: Any, default: int = 50) -> int:
        if value is None:
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default
