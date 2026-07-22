from __future__ import annotations

import json
import sqlite3
import uuid
from collections import defaultdict
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
    parent_span_id: str | None = None


@dataclass
class TraceSummary:
    trace_id: str
    started_at: datetime
    ended_at: datetime | None
    span_count: int
    status: str
    root_name: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanNode:
    span: TraceRecord
    children: list[SpanNode] = field(default_factory=list)


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

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    @classmethod
    def _row_to_record(cls, row: sqlite3.Row) -> TraceRecord:
        return TraceRecord(
            trace_id=row["trace_id"],
            span_id=row["span_id"],
            name=row["name"],
            started_at=cls._parse_dt(row["started_at"]) or datetime.now(UTC),
            ended_at=cls._parse_dt(row["ended_at"]),
            attributes=json.loads(row["attributes_json"] or "{}"),
            status=row["status"],
            error=row["error"],
            parent_span_id=row["parent_span_id"],
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
            parent_span_id=parent_span_id,
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

    def list_traces(self, *, limit: int = 20) -> list[TraceSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    trace_id,
                    MIN(started_at) AS started_at,
                    MAX(ended_at) AS ended_at,
                    COUNT(*) AS span_count,
                    MAX(CASE WHEN status != 'ok' THEN 1 ELSE 0 END) AS has_error
                FROM traces
                GROUP BY trace_id
                ORDER BY MIN(started_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            summaries: list[TraceSummary] = []
            for row in rows:
                root = conn.execute(
                    """
                    SELECT name, attributes_json
                    FROM traces
                    WHERE trace_id = ?
                    ORDER BY
                        CASE WHEN name = 'chat.completions' THEN 0 ELSE 1 END,
                        started_at ASC
                    LIMIT 1
                    """,
                    (row["trace_id"],),
                ).fetchone()
                summaries.append(
                    TraceSummary(
                        trace_id=row["trace_id"],
                        started_at=self._parse_dt(row["started_at"]) or datetime.now(UTC),
                        ended_at=self._parse_dt(row["ended_at"]),
                        span_count=row["span_count"],
                        status="error" if row["has_error"] else "ok",
                        root_name=root["name"] if root else "unknown",
                        attributes=json.loads(root["attributes_json"] or "{}") if root else {},
                    )
                )
            return summaries

    def latest_trace_id(self) -> str | None:
        for summary in self.list_traces(limit=20):
            if summary.attributes.get("passthrough_reason") == "continue_title":
                continue
            return summary.trace_id
        return None

    def get_spans(self, trace_id: str) -> list[TraceRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM traces
                WHERE trace_id = ?
                ORDER BY started_at ASC
                """,
                (trace_id,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def build_span_tree(spans: list[TraceRecord]) -> list[SpanNode]:
        if not spans:
            return []

        by_id = {span.span_id: span for span in spans}
        children: dict[str, list[TraceRecord]] = defaultdict(list)
        roots: list[TraceRecord] = []

        for span in spans:
            parent_id = span.parent_span_id
            if parent_id and parent_id in by_id:
                children[parent_id].append(span)
            else:
                roots.append(span)

        roots.sort(key=lambda span: span.started_at)

        def make_node(span: TraceRecord) -> SpanNode:
            child_spans = sorted(children.get(span.span_id, []), key=lambda s: s.started_at)
            return SpanNode(span=span, children=[make_node(child) for child in child_spans])

        return [make_node(root) for root in roots]
