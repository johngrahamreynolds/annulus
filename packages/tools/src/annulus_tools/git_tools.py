from __future__ import annotations

import subprocess
from pathlib import Path

MAX_OUTPUT_CHARS = 8000


def git_available(root: Path) -> bool:
    return (root / ".git").exists()


def run_git(root: Path, *args: str, timeout: int = 30) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, "", "git is not installed"
    except subprocess.TimeoutExpired:
        return 124, "", "git command timed out"
    return proc.returncode, proc.stdout, proc.stderr


def truncate_output(text: str, *, limit: int = MAX_OUTPUT_CHARS) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n… (truncated)", True
