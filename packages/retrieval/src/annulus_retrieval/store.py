from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChunkRow:
    id: int
    path: str
    start_line: int
    end_line: int
    content: str


_FTS_DDL = """
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    path,
    content,
    chunk_id UNINDEXED
);
"""


class IndexStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    indexed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    content TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
                """
            )
            self._ensure_fts_schema(conn)

    def _fts_has_chunk_id(self, conn: sqlite3.Connection) -> bool:
        try:
            conn.execute("SELECT chunk_id FROM chunks_fts LIMIT 0")
        except sqlite3.OperationalError:
            return False
        return True

    def _ensure_fts_schema(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'chunks_fts'"
        ).fetchone()
        if row and self._fts_has_chunk_id(conn):
            return
        conn.execute("DROP TABLE IF EXISTS chunks_fts")
        conn.executescript(_FTS_DDL)

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DROP TABLE IF EXISTS chunks_fts")
            conn.executescript(
                """
                DELETE FROM chunks;
                DELETE FROM files;
                """
            )
            self._ensure_fts_schema(conn)

    def _delete_path_rows(self, conn: sqlite3.Connection, path: str) -> None:
        conn.execute("DELETE FROM chunks_fts WHERE path = ?", (path,))
        conn.execute("DELETE FROM chunks WHERE path = ?", (path,))

    def delete_file(self, path: str) -> None:
        with self._connect() as conn:
            self._delete_path_rows(conn, path)
            conn.execute("DELETE FROM files WHERE path = ?", (path,))

    def list_files(self) -> list[tuple[str, float]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT path, mtime FROM files ORDER BY path").fetchall()
        return [(row["path"], row["mtime"]) for row in rows]

    def upsert_file(self, path: str, mtime: float, indexed_at: str) -> None:
        with self._connect() as conn:
            self._delete_path_rows(conn, path)
            conn.execute(
                "INSERT OR REPLACE INTO files(path, mtime, indexed_at) VALUES (?, ?, ?)",
                (path, mtime, indexed_at),
            )

    def insert_chunk(self, path: str, start_line: int, end_line: int, content: str) -> None:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chunks(path, start_line, end_line, content)
                VALUES (?, ?, ?, ?)
                """,
                (path, start_line, end_line, content),
            )
            chunk_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO chunks_fts(path, content, chunk_id) VALUES (?, ?, ?)",
                (path, content, chunk_id),
            )

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            files = conn.execute("SELECT COUNT(*) AS c FROM files").fetchone()["c"]
            chunks = conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()["c"]
        return {"files": files, "chunks": chunks}

    def search(self, query: str, limit: int = 5) -> list[ChunkRow]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.path, c.start_line, c.end_line, c.content
                FROM chunks_fts f
                JOIN chunks c ON c.id = f.chunk_id
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [
            ChunkRow(
                id=row["id"],
                path=row["path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                content=row["content"],
            )
            for row in rows
        ]
