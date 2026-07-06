from __future__ import annotations

import subprocess
from pathlib import Path

from annulus_core.config import load_settings
from annulus_retrieval.git_delta import collect_git_delta, head_commit
from annulus_retrieval.indexer import Indexer
from annulus_retrieval.retriever import Retriever


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_index_incremental_git_updates_and_removes(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    _git(workspace, "init")
    _git(workspace, "config", "user.email", "test@example.com")
    _git(workspace, "config", "user.name", "Test")

    (workspace / "hello.py").write_text("def annulus_greeting():\n    return 'hello'\n")
    _git(workspace, "add", "hello.py")
    _git(workspace, "commit", "-m", "init")

    settings = load_settings()
    settings.annulus_workspace_root = workspace
    settings.annulus_data_dir = tmp_path / ".annulus"
    settings.annulus_index_db = tmp_path / ".annulus" / "index.db"

    indexer = Indexer(settings)
    initial = indexer.index_all(rebuild=True)
    assert initial["files"] == 1

    (workspace / "hello.py").write_text("def annulus_greeting():\n    return 'hi'\n")
    (workspace / "other.py").write_text("value = 1\n")
    _git(workspace, "add", "hello.py", "other.py")
    _git(workspace, "commit", "-m", "add other")

    delta = collect_git_delta(workspace, since_commit=head_commit(workspace))
    assert delta is not None

    stats = indexer.index_incremental()
    assert stats["files"] >= 1
    assert indexer.store.stats()["files"] == 2

    retriever = Retriever(settings)
    assert retriever.search("value")

    (workspace / "other.py").unlink()
    _git(workspace, "add", "other.py")
    _git(workspace, "commit", "-m", "remove other")

    removed_stats = indexer.index_incremental()
    assert removed_stats.get("removed", 0) >= 1
    assert indexer.store.stats()["files"] == 1
    assert not retriever.search("value")
    assert retriever.search("hi")


def test_index_incremental_mtime_updates_and_removes(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "hello.py").write_text("def annulus_greeting():\n    return 'hello'\n")

    settings = load_settings()
    settings.annulus_workspace_root = workspace
    settings.annulus_data_dir = tmp_path / ".annulus"
    settings.annulus_index_db = tmp_path / ".annulus" / "index.db"

    indexer = Indexer(settings)
    initial = indexer.index_all(rebuild=True)
    assert initial["files"] == 1

    (workspace / "hello.py").write_text("def annulus_greeting():\n    return 'updated'\n")
    (workspace / "other.py").write_text("value = 1\n")

    stats = indexer.index_incremental()
    assert stats["strategy"] == "mtime"
    assert stats["files"] >= 1
    assert indexer.store.stats()["files"] == 2

    retriever = Retriever(settings)
    assert retriever.search("updated")
    assert retriever.search("value")

    (workspace / "other.py").unlink()

    removed_stats = indexer.index_incremental()
    assert removed_stats["strategy"] == "mtime"
    assert removed_stats.get("removed", 0) >= 1
    assert indexer.store.stats()["files"] == 1
    assert not retriever.search("value")
    assert retriever.search("updated")


def test_store_migrates_legacy_fts_schema_on_rebuild(tmp_path):
    import sqlite3

    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "hello.py").write_text("def annulus_greeting():\n    return 'hello'\n")

    settings = load_settings()
    settings.annulus_workspace_root = workspace
    settings.annulus_data_dir = tmp_path / ".annulus"
    settings.annulus_index_db = tmp_path / ".annulus" / "index.db"

    db_path = settings.resolve_index_db()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE files (
            path TEXT PRIMARY KEY,
            mtime REAL NOT NULL,
            indexed_at TEXT NOT NULL
        );
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            content TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            path,
            content,
            content='chunks',
            content_rowid='id'
        );
        """
    )
    conn.commit()
    conn.close()

    indexer = Indexer(settings)
    stats = indexer.index_all(rebuild=True)
    assert stats["files"] == 1
    assert Retriever(settings).search("annulus_greeting")
