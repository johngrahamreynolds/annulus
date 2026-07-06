from __future__ import annotations

from pathlib import Path

from annulus_trace.store import TraceStore


def _seed_chat_trace(store: TraceStore) -> str:
    root = store.start_span(
        "chat.completions",
        attributes={"profile": "local", "stream": False, "message_count": 1},
    )
    trace_id = root.trace_id
    store.end_span(root.span_id, attributes={"iterations": 2, "tools": ["ripgrep"]})

    retrieval = store.start_span(
        "retrieval.search",
        trace_id=trace_id,
        attributes={"query": "agent loop"},
    )
    store.end_span(retrieval.span_id, attributes={"hits": 2})

    iteration = store.start_span(
        "agent.iteration",
        trace_id=trace_id,
        attributes={"iteration": 1, "profile": "local"},
    )
    store.end_span(iteration.span_id, attributes={"streamed": True})

    tool = store.start_span(
        "tool.ripgrep",
        trace_id=trace_id,
        attributes={"args": {"pattern": "AgentRuntime"}},
    )
    store.end_span(tool.span_id, attributes={"tool": "ripgrep"})

    return trace_id


def test_list_traces_returns_recent_summaries(tmp_path: Path) -> None:
    db_path = tmp_path / "traces.db"
    store = TraceStore(db_path)
    trace_id = _seed_chat_trace(store)

    summaries = store.list_traces(limit=10)
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.trace_id == trace_id
    assert summary.span_count == 4
    assert summary.status == "ok"
    assert summary.root_name == "chat.completions"
    assert summary.attributes["profile"] == "local"


def test_get_spans_and_span_tree(tmp_path: Path) -> None:
    db_path = tmp_path / "traces.db"
    store = TraceStore(db_path)
    trace_id = _seed_chat_trace(store)

    spans = store.get_spans(trace_id)
    assert len(spans) == 4
    assert {span.name for span in spans} == {
        "chat.completions",
        "retrieval.search",
        "agent.iteration",
        "tool.ripgrep",
    }

    tree = TraceStore.build_span_tree(spans)
    assert len(tree) == 4
    assert all(not node.children for node in tree)


def test_build_span_tree_honors_parent_links(tmp_path: Path) -> None:
    db_path = tmp_path / "traces.db"
    store = TraceStore(db_path)

    root = store.start_span("chat.completions")
    child = store.start_span(
        "agent.iteration",
        trace_id=root.trace_id,
        parent_span_id=root.span_id,
    )
    store.end_span(child.span_id)
    store.end_span(root.span_id)

    tree = TraceStore.build_span_tree(store.get_spans(root.trace_id))
    assert len(tree) == 1
    assert tree[0].span.name == "chat.completions"
    assert len(tree[0].children) == 1
    assert tree[0].children[0].span.name == "agent.iteration"


def test_latest_trace_id(tmp_path: Path) -> None:
    db_path = tmp_path / "traces.db"
    store = TraceStore(db_path)
    assert store.latest_trace_id() is None

    first = _seed_chat_trace(store)
    assert store.latest_trace_id() == first

    second_root = store.start_span("chat.completions", attributes={"profile": "local-large"})
    store.end_span(second_root.span_id)
    assert store.latest_trace_id() == second_root.trace_id


def test_list_traces_marks_error_status(tmp_path: Path) -> None:
    db_path = tmp_path / "traces.db"
    store = TraceStore(db_path)
    root = store.start_span("chat.completions")
    store.end_span(root.span_id, status="error", error="boom")

    summaries = store.list_traces(limit=1)
    assert summaries[0].status == "error"
