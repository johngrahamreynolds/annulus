from __future__ import annotations

from annulus_core.config import load_settings
from annulus_retrieval.indexer import Indexer
from annulus_retrieval.retriever import Retriever


def test_index_and_search(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "hello.py").write_text("def annulus_greeting():\n    return 'hello'\n")

    settings = load_settings()
    settings.annulus_workspace_root = workspace
    settings.annulus_data_dir = tmp_path / ".annulus"
    settings.annulus_index_db = tmp_path / ".annulus" / "index.db"

    indexer = Indexer(settings)
    stats = indexer.index_all(rebuild=True)
    assert stats["files"] == 1
    assert stats["chunks"] >= 1

    retriever = Retriever(settings)
    hits = retriever.search("annulus_greeting")
    assert hits
    assert hits[0].path == "hello.py"
