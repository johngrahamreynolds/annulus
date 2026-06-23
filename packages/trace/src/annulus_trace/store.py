from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class TraceRecord:
    trace_id: str
    span_id: str
    name: str
    started_at: datetime
    ended_at: datetime | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    error: str | None = None


class TraceStore:
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
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT NOT NULL,
                    span_id TEXT PRIMARY KEY,
                    parent_span_id TEXT,
                    name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL DEFAULT 'ok',
                    error TEXT,
                    attributes_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_traces_trace_id ON traces(trace_id);
                CREATE INDEX IF NOT EXISTS idx_traces_started_at ON traces(started_at);
                """
            )

    def start_span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceRecord:
        record = TraceRecord(
            trace_id=trace_id or str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            name=name,
            started_at=datetime.now(UTC),
            attributes=attributes or {},
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO traces (
                    trace_id, span_id, parent_span_id, name,
                    started_at, status, attributes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.trace_id,
                    record.span_id,
                    parent_span_id,
                    record.name,
                    record.started_at.isoformat(),
                    record.status,
                    json.dumps(record.attributes),
                ),
            )
        return record

    def end_span(
        self,
        span_id: str,
        *,
        status: str = "ok",
        error: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        ended_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            if attributes:
                row = conn.execute(
                    "SELECT attributes_json FROM traces WHERE span_id = ?",
                    (span_id,),
                ).fetchone()
                merged = json.loads(row["attributes_json"]) if row else {}
                merged.update(attributes)
                conn.execute(
                    """
                    UPDATE traces
                    SET ended_at = ?, status = ?, error = ?, attributes_json = ?
                    WHERE span_id = ?
                    """,
                    (ended_at, status, error, json.dumps(merged), span_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE traces
                    SET ended_at = ?, status = ?, error = ?
                    WHERE span_id = ?
                    """,
                    (ended_at, status, error, span_id),
                )

    @contextmanager
    def span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[TraceRecord]:
        record = self.start_span(name, trace_id=trace_id, attributes=attributes)
        try:
            yield record
            self.end_span(record.span_id, status="ok")
        except Exception as exc:
            self.end_span(record.span_id, status="error", error=str(exc))
            raise
