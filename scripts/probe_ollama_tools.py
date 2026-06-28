#!/usr/bin/env python3
"""Probe Ollama model tool-calling behavior for Annulus compatibility (ADR-013)."""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

# Minimal ripgrep tool (matches Annulus registry shape)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ripgrep",
            "description": "Search file contents with ripgrep under the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex or literal pattern"},
                    "path": {"type": "string", "description": "Optional relative path", "default": "."},
                    "max_results": {"type": "integer", "description": "Max matches", "default": 50},
                },
                "required": ["pattern"],
            },
        },
    }
]

FULL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    *TOOLS,
]


def assemble_stream_message(chunks: list[dict]) -> dict:
    """Merge streamed OpenAI-style chunks into one assistant message."""
    message: dict = {"role": "assistant", "content": ""}
    tool_calls: dict[int, dict] = {}
    finish_reason = None

    for event in chunks:
        choice = (event.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}
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
        if choice.get("finish_reason"):
            finish_reason = choice["finish_reason"]

    if tool_calls:
        message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]
    message["_finish_reason"] = finish_reason
    return message


def chat(base: str, model: str, messages: list, *, stream: bool, tools: list | None, tool_choice: str | None) -> dict:
    payload: dict = {"model": model, "messages": messages, "stream": stream}
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    req = urllib.request.Request(
        f"{base.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        if stream:
            chunks = []
            for line in resp.read().decode().splitlines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                chunks.append(json.loads(data))
            return {"stream_chunks": len(chunks), "chunks": chunks, "last": chunks[-1] if chunks else None}
        return json.loads(resp.read())


def analyze_message(msg: dict) -> dict:
    content = msg.get("content") or ""
    tcs = msg.get("tool_calls") or []
    parsed_content_json = None
    if content.strip().startswith("{"):
        try:
            parsed_content_json = json.loads(content)
        except json.JSONDecodeError:
            pass
    return {
        "message_keys": sorted(msg.keys()),
        "finish_reason_hint": "tool_calls" if tcs else ("content_json" if parsed_content_json else "text"),
        "tool_calls_count": len(tcs),
        "tool_calls": tcs,
        "content_preview": content[:400] if content else "",
        "content_parsed_as_tool": parsed_content_json,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Probe Ollama tool calling for a model")
    p.add_argument("model", help="Ollama model tag, e.g. gpt-oss:20b")
    p.add_argument(
        "--base",
        default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        help="Ollama base URL (default: OLLAMA_HOST or http://127.0.0.1:11434)",
    )
    p.add_argument("--full-tools", action="store_true", help="Use Annulus read_file + ripgrep schemas")
    p.add_argument(
        "--prompt",
        default="Use the ripgrep tool now to search for TODO comments. Call the tool; do not explain.",
        help="User message sent to the model (workspace-independent; tools are not executed)",
    )
    args = p.parse_args()

    tools = FULL_TOOLS if args.full_tools else TOOLS
    prompt = args.prompt

    print(f"Model: {args.model}")
    print(f"Base:  {args.base}")
    print("Note:  probe talks to Ollama only — no Annulus gateway, no workspace, no tool execution.\n")

    for label, stream in [("non-stream", False), ("stream", True)]:
        print("=" * 60)
        print(label)
        try:
            if stream:
                result = chat(
                    args.base,
                    args.model,
                    [{"role": "user", "content": prompt}],
                    stream=True,
                    tools=tools,
                    tool_choice=None,
                )
                assembled = assemble_stream_message(result.get("chunks") or [])
                finish_reason = assembled.pop("_finish_reason", None)
                out = analyze_message(assembled)
                if finish_reason:
                    out["finish_reason"] = finish_reason
                print(json.dumps({"stream_chunks": result["stream_chunks"], "analysis": out}, indent=2))
            else:
                result = chat(
                    args.base,
                    args.model,
                    [{"role": "user", "content": prompt}],
                    stream=False,
                    tools=tools,
                    tool_choice="auto",
                )
                msg = result["choices"][0]["message"]
                out = analyze_message(msg)
                out["finish_reason"] = result["choices"][0].get("finish_reason")
                print(json.dumps(out, indent=2))
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}: {e.read().decode()[:500]}")
        except Exception as e:
            print(f"ERROR: {e}")
        print()


if __name__ == "__main__":
    main()
