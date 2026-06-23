from __future__ import annotations

from datetime import UTC, datetime

from annulus_core.config import AnnulusSettings

from annulus_retrieval.store import IndexStore


class Indexer:
    def __init__(self, settings: AnnulusSettings) -> None:
        self.settings = settings
        self.store = IndexStore(settings.resolve_index_db())
        self.root = settings.resolve_workspace_root()

    def index_all(self, *, rebuild: bool = False) -> dict[str, int]:
        if rebuild:
            self.store.clear()
        indexed_files = 0
        indexed_chunks = 0
        for file_path in self._iter_files():
            rel = str(file_path.relative_to(self.root))
            mtime = file_path.stat().st_mtime
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            self.store.upsert_file(rel, mtime, datetime.now(UTC).isoformat())
            for start_line, end_line, chunk in self._chunk_text(text):
                self.store.insert_chunk(rel, start_line, end_line, chunk)
                indexed_chunks += 1
            indexed_files += 1
        return {"files": indexed_files, "chunks": indexed_chunks}

    def _iter_files(self):
        exclude_dirs = set(self.settings.retrieval.exclude_dirs)
        exclude_ext = set(self.settings.retrieval.exclude_extensions)
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in exclude_dirs for part in path.parts):
                continue
            if path.suffix in exclude_ext:
                continue
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
            # step back by overlap
            overlap_chars = 0
            back = idx - 1
            while back > start and overlap_chars < overlap:
                overlap_chars += len(lines[back]) + 1
                back -= 1
            start = max(start + 1, back + 1)
