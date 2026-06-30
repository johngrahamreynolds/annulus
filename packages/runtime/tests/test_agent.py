from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from annulus_core.config import AnnulusSettings, ModelProfile
from annulus_runtime.agent import AgentRuntime, _prepend_system_context
from annulus_runtime.streaming import (
    assemble_stream_message,
    assistant_visible_text,
    normalize_stream_chunk,
    stream_completion_content,
    to_cli_stream_chunk,
)


def test_prepend_system_context_returns_flat_message_list():
    messages = [{"role": "user", "content": "Hello"}]
    updated = _prepend_system_context(messages, "repo context")
    assert updated == [
        {"role": "system", "content": "repo context"},
        {"role": "user", "content": "Hello"},
    ]
    assert not any(isinstance(m, list) for m in updated)


def test_assistant_visible_text_prefers_content():
    assert assistant_visible_text({"content": "answer", "reasoning": "think"}) == "answer"


def test_assistant_visible_text_falls_back_to_reasoning():
    assert assistant_visible_text({"content": "", "reasoning": "think"}) == "think"


def test_to_cli_stream_chunk_maps_reasoning_to_content():
    event = {
        "choices": [{"delta": {"reasoning": "Once upon a time"}, "finish_reason": None}],
    }
    raw = to_cli_stream_chunk(event)
    assert raw is not None
    payload = json.loads(raw.decode().split("data: ", 1)[1].strip())
    assert payload["choices"][0]["delta"]["content"] == "Once upon a time"


def test_normalize_stream_chunk_expose_reasoning():
    event = {
        "choices": [{"delta": {"reasoning": "Thinking"}, "finish_reason": None}],
    }
    raw = normalize_stream_chunk(event, expose_reasoning=True)
    assert raw is not None
    payload = json.loads(raw.decode().split("data: ", 1)[1].strip())
    delta = payload["choices"][0]["delta"]
    assert delta["reasoning_content"] == "Thinking"
    assert "reasoning" not in delta
    assert "content" not in delta


def test_normalize_stream_chunk_keeps_content_and_reasoning_separate():
    event = {
        "choices": [
            {
                "delta": {"reasoning": "Plan:", "content": "Answer"},
                "finish_reason": None,
            }
        ],
    }
    raw = normalize_stream_chunk(event, expose_reasoning=True)
    assert raw is not None
    delta = json.loads(raw.decode().split("data: ", 1)[1].strip())["choices"][0]["delta"]
    assert delta["reasoning_content"] == "Plan:"
    assert delta["content"] == "Answer"


def test_assemble_stream_message_merges_tool_calls():
    events = [
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "function": {"name": "ripgrep", "arguments": '{"pat'},
                            }
                        ]
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {"index": 0, "function": {"arguments": 'tern": "TODO"}'}}
                        ]
                    }
                }
            ]
        },
    ]
    message = assemble_stream_message(events)
    assert message["tool_calls"][0]["function"]["name"] == "ripgrep"
    assert json.loads(message["tool_calls"][0]["function"]["arguments"]) == {"pattern": "TODO"}


@pytest.mark.asyncio
async def test_stream_completion_content_emits_openai_sse():
    chunks = [
        chunk.decode()
        async for chunk in stream_completion_content("Hello", model="local", chunk_chars=0)
    ]
    assert chunks[-1].strip() == "data: [DONE]"
    payload_lines = [line for line in chunks if line.startswith("data: ") and "[DONE]" not in line]
    assert len(payload_lines) == 2
    first = json.loads(payload_lines[0][6:])
    assert first["choices"][0]["delta"]["content"] == "Hello"
    last = json.loads(payload_lines[1][6:])
    assert last["choices"][0]["finish_reason"] == "stop"


def _settings(*, tools_enabled: bool = True) -> AnnulusSettings:
    settings = AnnulusSettings()
    settings.agent.tools_enabled = tools_enabled
    settings.agent.retrieval_enabled = False
    settings.models.profiles["local"] = ModelProfile(
        provider="ollama",
        model="llama3.1:8b",
        supports_tools=True,
    )
    settings.router.default_profile = "local"
    return settings


def _sse(*events: dict[str, Any], done: bool = True) -> list[bytes]:
    chunks = [f"data: {json.dumps(event)}\n\n".encode() for event in events]
    if done:
        chunks.append(b"data: [DONE]\n\n")
    return chunks


@pytest.mark.asyncio
async def test_stream_run_forwards_live_content_without_tools():
    settings = _settings()
    router = MagicMock()
    router.resolve_profile.return_value = (
        "local",
        settings.models.profiles["local"],
    )
    router.build_payload.side_effect = lambda **kwargs: kwargs

    async def fake_stream(*args, **kwargs):
        for chunk in _sse(
            {"choices": [{"delta": {"role": "assistant", "content": "Once "}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": "upon a time"}, "finish_reason": None}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ):
            yield chunk

    router.stream = fake_stream

    runtime = AgentRuntime(
        settings=settings,
        router=router,
        retriever=MagicMock(),
        tools=MagicMock(),
        trace_store=MagicMock(),
    )

    raw = [chunk.decode() async for chunk in runtime.stream_run(messages=[{"role": "user", "content": "Story"}])]
    combined = "".join(raw)
    assert "Once " in combined
    assert "upon a time" in combined
    assert "[DONE]" in combined


@pytest.mark.asyncio
async def test_stream_run_executes_tools_and_streams_answer():
    settings = _settings()
    router = MagicMock()
    router.resolve_profile.return_value = (
        "local",
        settings.models.profiles["local"],
    )
    router.build_payload.side_effect = lambda **kwargs: kwargs

    tool_stream = _sse(
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "function": {
                                    "name": "ripgrep",
                                    "arguments": '{"pattern": "TODO"}',
                                },
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ]
        },
    )
    answer_stream = _sse(
        {"choices": [{"delta": {"content": "Found "}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "nothing."}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    )
    streams = [tool_stream, answer_stream]

    async def fake_stream(*args, **kwargs):
        for chunk in streams.pop(0):
            yield chunk

    router.stream = fake_stream

    tools = MagicMock()
    tools.execute.return_value = "(no matches)"

    runtime = AgentRuntime(
        settings=settings,
        router=router,
        retriever=MagicMock(),
        tools=tools,
        trace_store=MagicMock(),
    )

    raw = [chunk.decode() async for chunk in runtime.stream_run(messages=[{"role": "user", "content": "Find TODOs"}])]
    combined = "".join(raw)
    assert "Found " in combined
    assert "nothing." in combined
    assert '"status": "tool"' in combined
    tools.execute.assert_called_once_with("ripgrep", {"pattern": "TODO"})


@pytest.mark.asyncio
async def test_stream_run_passthrough_when_tools_disabled():
    settings = _settings()
    profile = ModelProfile(provider="ollama", model="llama3.2:3b", supports_tools=False)
    settings.models.profiles["local-fast"] = profile

    router = MagicMock()
    router.resolve_profile.return_value = ("local-fast", profile)
    router.build_payload.return_value = {"model": "llama3.2:3b", "stream": True}

    async def fake_stream(*args, **kwargs):
        yield b"data: {\"choices\":[{\"delta\":{\"content\":\"Hi\"}}]}\n\n"
        yield b"data: [DONE]\n\n"

    router.stream = fake_stream

    runtime = AgentRuntime(
        settings=settings,
        router=router,
        retriever=MagicMock(),
        tools=MagicMock(),
        trace_store=MagicMock(),
    )

    raw = [
        chunk
        async for chunk in runtime.stream_run(
            messages=[{"role": "user", "content": "Hi"}],
            profile_name="local-fast",
        )
    ]
    assert b"Hi" in b"".join(raw)


@pytest.mark.asyncio
async def test_stream_run_maps_reasoning_deltas_live():
    settings = _settings()
    settings.models.profiles["local"] = ModelProfile(
        provider="ollama",
        model="llama3.1:8b",
        supports_tools=True,
        expose_reasoning=True,
    )
    router = MagicMock()
    router.resolve_profile.return_value = (
        "local",
        settings.models.profiles["local"],
    )
    router.build_payload.side_effect = lambda **kwargs: kwargs

    async def fake_stream(*args, **kwargs):
        for chunk in _sse(
            {"choices": [{"delta": {"reasoning": "Backend classes"}, "finish_reason": None}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ):
            yield chunk

    router.stream = fake_stream

    runtime = AgentRuntime(
        settings=settings,
        router=router,
        retriever=MagicMock(),
        tools=MagicMock(),
        trace_store=MagicMock(),
    )

    raw = [chunk.decode() async for chunk in runtime.stream_run(messages=[{"role": "user", "content": "Hi"}])]
    assert any("reasoning_content" in line and "Backend classes" in line for line in raw)


def _runtime(settings: AnnulusSettings, *, retrieval_enabled: bool = False) -> AgentRuntime:
    settings.agent.retrieval_enabled = retrieval_enabled
    return AgentRuntime(
        settings=settings,
        router=MagicMock(),
        retriever=MagicMock(),
        tools=MagicMock(),
        trace_store=MagicMock(),
    )


def test_prepare_messages_appends_tool_prompt_after_client_system():
    settings = AnnulusSettings()
    settings.agent.tool_system_prompt = "<annulus_tools>use tools</annulus_tools>"
    runtime = _runtime(settings)
    profile = ModelProfile(provider="ollama", model="gemma4:12b", supports_tools=True)

    working, _ = runtime._prepare_messages(
        [
            {"role": "system", "content": "<important_rules>agent mode</important_rules>"},
            {"role": "user", "content": "Use ripgrep"},
        ],
        trace_id=None,
        profile=profile,
        tools_enabled=True,
    )

    system = working[0]["content"]
    assert system.index("<important_rules>") < system.index("<annulus_tools>")
    assert "use tools" in system


def test_prepare_messages_skips_tool_prompt_when_tools_disabled():
    settings = AnnulusSettings()
    settings.agent.tool_system_prompt = "<annulus_tools>use tools</annulus_tools>"
    runtime = _runtime(settings)
    profile = ModelProfile(provider="ollama", model="qwen", supports_tools=False)

    working, _ = runtime._prepare_messages(
        [{"role": "user", "content": "Hello"}],
        trace_id=None,
        profile=profile,
        tools_enabled=False,
    )

    assert all("<annulus_tools>" not in str(m.get("content", "")) for m in working)


def test_prepare_messages_profile_system_prompt_overrides_default():
    settings = AnnulusSettings()
    settings.agent.tool_system_prompt = "<annulus_tools>default</annulus_tools>"
    runtime = _runtime(settings)
    profile = ModelProfile(
        provider="ollama",
        model="gemma4:26b",
        supports_tools=True,
        system_prompt="<annulus_tools>override</annulus_tools>",
    )

    working, _ = runtime._prepare_messages(
        [{"role": "user", "content": "Use ripgrep"}],
        trace_id=None,
        profile=profile,
        tools_enabled=True,
    )

    assert "override" in working[0]["content"]
    assert "default" not in working[0]["content"]
