from __future__ import annotations

from annulus_core.config import AnnulusSettings
from annulus_tools.executor import ToolExecutor


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
