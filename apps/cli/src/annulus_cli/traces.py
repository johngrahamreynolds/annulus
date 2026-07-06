from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any

import typer
from annulus_core.config import load_settings
from annulus_trace.store import SpanNode, TraceStore, TraceSummary
from typer import Option

traces_app = typer.Typer(help="Inspect agent run spans in .annulus/traces.db")


def _store() -> TraceStore:
    settings = load_settings()
    return TraceStore(settings.resolve_trace_db())


def _format_duration(started_at: datetime, ended_at: datetime | None) -> str:
    if ended_at is None:
        return "—"
    seconds = max(0.0, (ended_at - started_at).total_seconds())
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


def _format_attributes(attributes: dict[str, Any]) -> str:
    if not attributes:
        return ""
    parts = [f"{key}={attributes[key]}" for key in sorted(attributes)]
    return "  " + " ".join(parts)


def _summary_to_dict(summary: TraceSummary) -> dict[str, Any]:
    return {
        "trace_id": summary.trace_id,
        "started_at": summary.started_at.isoformat(),
        "ended_at": summary.ended_at.isoformat() if summary.ended_at else None,
        "span_count": summary.span_count,
        "status": summary.status,
        "root_name": summary.root_name,
        "attributes": summary.attributes,
    }


def _span_to_dict(span) -> dict[str, Any]:
    return {
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "parent_span_id": span.parent_span_id,
        "name": span.name,
        "started_at": span.started_at.isoformat(),
        "ended_at": span.ended_at.isoformat() if span.ended_at else None,
        "status": span.status,
        "error": span.error,
        "attributes": span.attributes,
    }


def _node_to_dict(node: SpanNode) -> dict[str, Any]:
    data = _span_to_dict(node.span)
    if node.children:
        data["children"] = [_node_to_dict(child) for child in node.children]
    return data


def _print_span_node(node: SpanNode, *, indent: int = 0) -> None:
    span = node.span
    prefix = "  " * indent
    duration = _format_duration(span.started_at, span.ended_at)
    status = span.status if span.status == "ok" else f"{span.status}"
    line = f"{prefix}{span.name}  {status}  {duration}{_format_attributes(span.attributes)}"
    typer.echo(line)
    if span.error:
        typer.echo(f"{prefix}  error: {span.error}", err=True)
    for child in node.children:
        _print_span_node(child, indent=indent + 1)


def _print_trace_show(trace_id: str, store: TraceStore) -> None:
    spans = store.get_spans(trace_id)
    if not spans:
        typer.echo(f"No trace found for id: {trace_id}", err=True)
        raise typer.Exit(code=1)

    started = min(span.started_at for span in spans)
    ended_values = [span.ended_at for span in spans if span.ended_at]
    ended = max(ended_values) if ended_values else None
    status = "error" if any(span.status != "ok" for span in spans) else "ok"

    typer.echo(f"trace_id: {trace_id}")
    typer.echo(f"started:  {started.isoformat()}")
    if ended:
        typer.echo(f"ended:    {ended.isoformat()}")
    typer.echo(f"spans:    {len(spans)}  status={status}")
    typer.echo("")
    for node in TraceStore.build_span_tree(spans):
        _print_span_node(node)


@traces_app.command("list")
def traces_list(
    limit: Annotated[int, Option("--limit", "-n", help="Maximum traces to list")] = 20,
    json_output: Annotated[bool, Option("--json", help="Emit JSON")] = False,
) -> None:
    """List recent chat/agent traces."""
    store = _store()
    summaries = store.list_traces(limit=limit)
    if json_output:
        typer.echo(json.dumps([_summary_to_dict(item) for item in summaries], indent=2))
        return

    if not summaries:
        typer.echo("No traces found.")
        return

    typer.echo(f"{'TRACE ID':<38} {'STARTED':<28} {'SPANS':>5}  STATUS")
    for item in summaries:
        started = item.started_at.isoformat()
        typer.echo(f"{item.trace_id:<38} {started:<28} {item.span_count:>5}  {item.status}")


@traces_app.command("show")
def traces_show(
    trace_id: Annotated[
        str,
        typer.Argument(help="Trace id (from list or X-Annulus-Trace-Id header)"),
    ],
    json_output: Annotated[bool, Option("--json", help="Emit JSON")] = False,
) -> None:
    """Show span tree for a trace."""
    store = _store()
    spans = store.get_spans(trace_id)
    if not spans:
        typer.echo(f"No trace found for id: {trace_id}", err=True)
        raise typer.Exit(code=1)

    if json_output:
        tree = TraceStore.build_span_tree(spans)
        typer.echo(
            json.dumps(
                {
                    "trace_id": trace_id,
                    "spans": [_node_to_dict(node) for node in tree],
                },
                indent=2,
            )
        )
        return

    _print_trace_show(trace_id, store)


@traces_app.command("last")
def traces_last(
    json_output: Annotated[bool, Option("--json", help="Emit JSON")] = False,
) -> None:
    """Show the most recent trace (handy after annulus chat)."""
    store = _store()
    trace_id = store.latest_trace_id()
    if not trace_id:
        typer.echo("No traces found.", err=True)
        raise typer.Exit(code=1)

    if json_output:
        spans = store.get_spans(trace_id)
        tree = TraceStore.build_span_tree(spans)
        typer.echo(
            json.dumps(
                {
                    "trace_id": trace_id,
                    "spans": [_node_to_dict(node) for node in tree],
                },
                indent=2,
            )
        )
        return

    _print_trace_show(trace_id, store)
