from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from annulus_core.config import AnnulusSettings

from annulus_retrieval.git_delta import collect_git_delta, git_available, head_commit
from annulus_retrieval.meta import IndexMeta
from annulus_retrieval.store import IndexStore


class Indexer:
    def __init__(self, settings: AnnulusSettings) -> None:
        self.settings = settings
        self.store = IndexStore(settings.resolve_index_db())
        self.root = settings.resolve_workspace_root()

    def resolve_meta_path(self) -> Path:
        return self.settings.annulus_data_dir / "index_meta.json"

    def index_all(self, *, rebuild: bool = False) -> dict[str, Any]:
        if rebuild:
            self.store.clear()
        indexed_files = 0
        indexed_chunks = 0
        for file_path in self._iter_files():
            rel = str(file_path.relative_to(self.root))
            chunk_count = self._index_path(rel, file_path)
            if chunk_count is None:
                continue
            indexed_files += 1
            indexed_chunks += chunk_count
        self._save_meta(strategy="git" if git_available(self.root) else "mtime")
        return {"files": indexed_files, "chunks": indexed_chunks, "mode": "full"}

    def index_incremental(self) -> dict[str, Any]:
        stats = self.store.stats()
        if stats["files"] == 0:
            full = self.index_all(rebuild=False)
            full["mode"] = "initial_full"
            return full

        if git_available(self.root):
            result = self._index_git_delta()
        else:
            result = self._index_mtime_delta()
        self._save_meta(strategy="git" if git_available(self.root) else "mtime")
        result["mode"] = "incremental"
        return result

    def _index_git_delta(self) -> dict[str, Any]:
        meta = IndexMeta.load(self.resolve_meta_path())
        since = meta.last_commit if meta else None
        if not since:
            return self._index_mtime_delta()

        delta = collect_git_delta(self.root, since_commit=since)
        if delta is None:
            return self._index_mtime_delta()

        removed = 0
        updated_files = 0
        indexed_chunks = 0

        for rel in delta.deleted:
            if self._remove_path(rel):
                removed += 1

        for rel in delta.added_or_modified:
            outcome = self._index_relative(rel)
            if outcome is None:
                continue
            if outcome == 0 and self._remove_path(rel):
                removed += 1
            elif outcome > 0:
                updated_files += 1
                indexed_chunks += outcome

        return {
            "files": updated_files,
            "chunks": indexed_chunks,
            "removed": removed,
            "strategy": "git",
            "head_commit": delta.head_commit,
        }

    def _index_mtime_delta(self) -> dict[str, Any]:
        removed = 0
        updated_files = 0
        indexed_chunks = 0
        indexed_paths = {path: mtime for path, mtime in self.store.list_files()}

        for rel, stored_mtime in list(indexed_paths.items()):
            file_path = self.root / rel
            if not file_path.is_file() or not self._should_index(file_path):
                if self._remove_path(rel):
                    removed += 1
                continue
            current_mtime = file_path.stat().st_mtime
            if current_mtime != stored_mtime:
                outcome = self._index_path(rel, file_path)
                if outcome is None:
                    if self._remove_path(rel):
                        removed += 1
                else:
                    updated_files += 1
                    indexed_chunks += outcome

        for file_path in self._iter_files():
            rel = str(file_path.relative_to(self.root))
            if rel in indexed_paths:
                continue
            outcome = self._index_path(rel, file_path)
            if outcome is None:
                continue
            updated_files += 1
            indexed_chunks += outcome

        commit = head_commit(self.root)
        return {
            "files": updated_files,
            "chunks": indexed_chunks,
            "removed": removed,
            "strategy": "mtime",
            "head_commit": commit,
        }

    def _index_relative(self, rel: str) -> int | None:
        file_path = self.root / rel
        if not file_path.is_file() or not self._should_index(file_path):
            return None
        return self._index_path(rel, file_path)

    def _index_path(self, rel: str, file_path: Path) -> int | None:
        mtime = file_path.stat().st_mtime
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
        indexed_at = datetime.now(UTC).isoformat()
        self.store.upsert_file(rel, mtime, indexed_at)
        chunk_count = 0
        for start_line, end_line, chunk in self._chunk_text(text):
            self.store.insert_chunk(rel, start_line, end_line, chunk)
            chunk_count += 1
        return chunk_count

    def _remove_path(self, rel: str) -> bool:
        indexed_paths = {path for path, _ in self.store.list_files()}
        if rel not in indexed_paths:
            return False
        self.store.delete_file(rel)
        return True

    def _save_meta(self, *, strategy: str) -> None:
        IndexMeta(
            last_commit=head_commit(self.root),
            strategy=strategy,
            indexed_at=datetime.now(UTC).isoformat(),
        ).save(self.resolve_meta_path())

    def _should_index(self, path: Path) -> bool:
        if not path.is_file():
            return False
        exclude_dirs = set(self.settings.retrieval.exclude_dirs)
        exclude_ext = set(self.settings.retrieval.exclude_extensions)
        if any(part in exclude_dirs for part in path.parts):
            return False
        return path.suffix not in exclude_ext

    def _iter_files(self):
        for path in sorted(self.root.rglob("*")):
            if self._should_index(path):
                yield path

    def _chunk_text(self, text: str):
        max_chars = self.settings.retrieval.max_chunk_chars
        overlap = self.settings.retrieval.overlap_chars
        lines = text.splitlines()
        if not lines:
            return

        start = 0
        while start < len(lines):
            chunk_lines: list[str] = []
            char_count = 0
            idx = start
            while idx < len(lines):
                line = lines[idx]
                if chunk_lines and char_count + len(line) + 1 > max_chars:
                    break
                chunk_lines.append(line)
                char_count += len(line) + 1
                idx += 1
            if not chunk_lines:
                break
            end = idx - 1
            yield start + 1, end + 1, "\n".join(chunk_lines)
            if idx >= len(lines):
                break
            overlap_chars = 0
            back = idx - 1
            while back > start and overlap_chars < overlap:
                overlap_chars += len(lines[back]) + 1
                back -= 1
            start = max(start + 1, back + 1)
