from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from annulus_core.config import AnnulusSettings
from annulus_tools.executor import ToolExecutor


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_ripgrep_sanitizes_invalid_model_args(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNULUS_WORKSPACE_ROOT", str(tmp_path))
    (tmp_path / "sample.py").write_text("# TODO fix this\n", encoding="utf-8")

    settings = AnnulusSettings()
    executor = ToolExecutor(settings)
    result = executor.execute(
        "ripgrep",
        {"pattern": "TODO", "path": "", "max_results": "-1"},
    )

    assert "TODO fix this" in result
    assert "error: Found argument '-1'" not in result


def test_git_status_reports_branch_and_dirty_files(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNULUS_WORKSPACE_ROOT", str(tmp_path))
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "tracked.py").write_text("a = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.py")
    _git(tmp_path, "commit", "-m", "init")
    (tmp_path / "tracked.py").write_text("a = 2\n", encoding="utf-8")
    (tmp_path / "new.py").write_text("b = 1\n", encoding="utf-8")

    settings = AnnulusSettings()
    executor = ToolExecutor(settings)
    payload = json.loads(executor.execute("git_status", {}))

    assert payload["branch"] == "main" or payload["branch"] != "(detached)"
    assert "tracked.py" in payload["status"]
    assert "new.py" in payload["status"]


def test_git_diff_unstaged_and_staged(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNULUS_WORKSPACE_ROOT", str(tmp_path))
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "file.py").write_text("before\n", encoding="utf-8")
    _git(tmp_path, "add", "file.py")
    _git(tmp_path, "commit", "-m", "init")

    (tmp_path / "file.py").write_text("after\n", encoding="utf-8")
    settings = AnnulusSettings()
    executor = ToolExecutor(settings)

    unstaged = json.loads(executor.execute("git_diff", {}))
    assert "after" in unstaged["diff"]
    assert unstaged["staged"] is False

    _git(tmp_path, "add", "file.py")
    staged = json.loads(executor.execute("git_diff", {"staged": True}))
    assert "after" in staged["diff"]
    assert staged["staged"] is True


def test_git_diff_scoped_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNULUS_WORKSPACE_ROOT", str(tmp_path))
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "a.py").write_text("a\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b\n", encoding="utf-8")
    _git(tmp_path, "add", "a.py", "b.py")
    _git(tmp_path, "commit", "-m", "init")
    (tmp_path / "a.py").write_text("a2\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("b2\n", encoding="utf-8")

    settings = AnnulusSettings()
    executor = ToolExecutor(settings)
    payload = json.loads(executor.execute("git_diff", {"path": "a.py"}))

    assert "a2" in payload["diff"]
    assert "b2" not in payload["diff"]


def test_git_tools_error_when_not_a_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNULUS_WORKSPACE_ROOT", str(tmp_path))
    settings = AnnulusSettings()
    executor = ToolExecutor(settings)

    status = json.loads(executor.execute("git_status", {}))
    diff = json.loads(executor.execute("git_diff", {}))

    assert status["error"] == "Not a git repository"
    assert diff["error"] == "Not a git repository"


def test_git_diff_rejects_path_outside_sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNULUS_WORKSPACE_ROOT", str(tmp_path))
    _git(tmp_path, "init")
    settings = AnnulusSettings()
    executor = ToolExecutor(settings)

    with pytest.raises(ValueError, match="escapes workspace"):
        executor.execute("git_diff", {"path": "../outside"})
