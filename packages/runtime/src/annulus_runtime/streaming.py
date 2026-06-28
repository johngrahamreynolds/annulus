from __future__ import annotations

import copy
import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any


def assistant_visible_text(message: dict[str, Any]) -> str:
    """Return user-visible assistant text from an Ollama/OpenAI message."""
    content = message.get("content")
    if content is not None and str(content).strip():
        return str(content)
    reasoning = message.get("reasoning")
    if reasoning is not None and str(reasoning).strip():
        return str(reasoning)
    return ""


def stream_status_event(*, model: str, status: str, detail: str = "") -> bytes:
    payload: dict[str, Any] = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": None}],
        "annulus": {"status": status, "detail": detail},
    }
    return f"data: {json.dumps(payload)}\n\n".encode()


def iter_sse_events(raw: bytes, buffer: str) -> tuple[list[dict[str, Any]], str]:
    """Parse SSE `data:` events from streamed bytes, returning leftover buffer text."""
    buffer += raw.decode(errors="replace")
    events: list[dict[str, Any]] = []
    while "\n\n" in buffer:
        block, buffer = buffer.split("\n\n", 1)
        for line in block.splitlines():
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                events.append({"__done__": True})
                continue
            try:
                events.append(json.loads(data))
            except json.JSONDecodeError:
                continue
    return events, buffer


def event_has_tool_call_delta(event: dict[str, Any]) -> bool:
    if event.get("__done__"):
        return False
    try:
        delta = event["choices"][0]["delta"]
    except (KeyError, IndexError, TypeError):
        return False
    return bool(delta.get("tool_calls"))


def to_cli_stream_chunk(event: dict[str, Any]) -> bytes | None:
    """Normalize a provider chunk for clients that only render delta.content."""
    if event.get("__done__"):
        return b"data: [DONE]\n\n"

    try:
        choice = event["choices"][0]
        delta = dict(choice.get("delta") or {})
    except (KeyError, IndexError, TypeError):
        return None

    if delta.get("tool_calls"):
        return None

    if delta.get("reasoning") and not delta.get("content"):
        reasoning = delta["reasoning"]
        delta = {k: v for k, v in delta.items() if k != "reasoning"}
        delta["content"] = reasoning

    if not delta and not choice.get("finish_reason"):
        return None

    normalized = copy.deepcopy(event)
    normalized["choices"][0]["delta"] = delta
    return f"data: {json.dumps(normalized)}\n\n".encode()


def assemble_stream_message(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge streamed OpenAI-style chunks into a single assistant message."""
    message: dict[str, Any] = {"role": "assistant", "content": ""}
    tool_calls: dict[int, dict[str, Any]] = {}

    for event in events:
        if event.get("__done__"):
            continue
        try:
            choice = event["choices"][0]
            delta = choice.get("delta") or {}
        except (KeyError, IndexError, TypeError):
            continue

        if role := delta.get("role"):
            message["role"] = role
        if piece := delta.get("content"):
            message["content"] = f"{message.get('content') or ''}{piece}"
        if piece := delta.get("reasoning"):
            message["reasoning"] = f"{message.get('reasoning') or ''}{piece}"

        for call in delta.get("tool_calls") or []:
            index = int(call.get("index") or 0)
            entry = tool_calls.setdefault(
                index,
                {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
            )
            if call_id := call.get("id"):
                entry["id"] = call_id
            fn = call.get("function") or {}
            if name := fn.get("name"):
                entry["function"]["name"] = name
            if args := fn.get("arguments"):
                entry["function"]["arguments"] = f"{entry['function']['arguments']}{args}"

    if tool_calls:
        message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]

    return message


async def stream_completion_content(
    content: str,
    *,
    model: str,
    completion_id: str | None = None,
    chunk_chars: int = 64,
) -> AsyncIterator[bytes]:
    """Emit OpenAI-compatible SSE chunks for a completed assistant message."""
    cid = completion_id or f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    if content:
        if chunk_chars <= 0 or len(content) <= chunk_chars:
            pieces = [content]
        else:
            pieces = [content[i : i + chunk_chars] for i in range(0, len(content), chunk_chars)]

        for index, piece in enumerate(pieces):
            delta: dict[str, Any] = {"content": piece}
            if index == 0:
                delta["role"] = "assistant"
            chunk = {
                "id": cid,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": delta,
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n".encode()

    final = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final)}\n\n".encode()
    yield b"data: [DONE]\n\n"
