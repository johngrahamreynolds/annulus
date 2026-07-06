from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitDelta:
    added_or_modified: list[str]
    deleted: list[str]
    head_commit: str


def git_available(root: Path) -> bool:
    return (root / ".git").exists()


def head_commit(root: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    commit = proc.stdout.strip()
    return commit or None


def collect_git_delta(root: Path, *, since_commit: str | None) -> GitDelta | None:
    commit = head_commit(root)
    if not commit:
        return None

    if not since_commit:
        return GitDelta(added_or_modified=[], deleted=[], head_commit=commit)

    changed = _git_lines(
        root,
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=ACMRD", since_commit],
    )
    deleted = _git_lines(
        root,
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=D", since_commit],
    )
    untracked = _git_lines(
        root,
        ["git", "-C", str(root), "ls-files", "-o", "--exclude-standard"],
    )

    modified = sorted(set(changed) | set(untracked) - set(deleted))
    return GitDelta(
        added_or_modified=modified,
        deleted=sorted(set(deleted)),
        head_commit=commit,
    )


def _git_lines(root: Path, cmd: list[str]) -> list[str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode not in (0, 1):
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
