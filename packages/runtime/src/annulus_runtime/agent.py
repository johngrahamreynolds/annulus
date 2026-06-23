from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from annulus_core.config import AnnulusSettings
from annulus_retrieval.retriever import Retriever
from annulus_router.router import ModelRouter
from annulus_tools.executor import ToolExecutor
from annulus_tools.registry import tool_schemas
from annulus_trace.store import TraceStore


@dataclass
class AgentRunResult:
    message: dict[str, Any]
    profile_name: str
    escalated: bool = False
    retrieval_hits: list[str] = field(default_factory=list)
    tool_calls: list[str] = field(default_factory=list)
    iterations: int = 0


class AgentRuntime:
    def __init__(
        self,
        settings: AnnulusSettings,
        router: ModelRouter,
        retriever: Retriever,
        tools: ToolExecutor,
        trace_store: TraceStore,
    ) -> None:
        self.settings = settings
        self.router = router
        self.retriever = retriever
        self.tools = tools
        self.trace_store = trace_store

    async def run(
        self,
        *,
        messages: list[dict[str, Any]],
        profile_name: str | None = None,
        trace_id: str | None = None,
        stream: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> AgentRunResult | dict[str, Any]:
        requested = profile_name
        profile_key, profile = self.router.resolve_profile(requested)
        working = [dict(m) for m in messages]
        retrieval_hits: list[str] = []
        tool_names: list[str] = []

        if self.settings.agent.retrieval_enabled:
            query = _last_user_message(working)
            if query:
                span = self.trace_store.start_span(
                    "retrieval.search",
                    trace_id=trace_id,
                    attributes={"query": query[:200]},
                )
                chunks = self.retriever.search(query)
                self.trace_store.end_span(
                    span.span_id,
                    attributes={"hits": len(chunks)},
                )
                if chunks:
                    context_block = _format_retrieval_context(chunks)
                    working = _prepend_system_context(working, context_block)
                    retrieval_hits = [
                        f"{c.path}:{c.start_line}-{c.end_line}" for c in chunks
                    ]

        if stream:
            payload = self.router.build_payload(
                profile=profile,
                messages=working,
                stream=True,
                extra=extra,
            )
            return {
                "mode": "stream",
                "profile_key": profile_key,
                "profile": profile,
                "payload": payload,
            }

        tools_enabled = self.settings.agent.tools_enabled and profile.supports_tools
        max_iters = self.settings.agent.max_iterations

        for iteration in range(max_iters):
            payload_extra = dict(extra or {})
            if tools_enabled:
                payload_extra["tools"] = tool_schemas()
                payload_extra["tool_choice"] = "auto"

            payload = self.router.build_payload(
                profile=profile,
                messages=working,
                stream=False,
                extra=payload_extra,
            )

            iter_span = self.trace_store.start_span(
                "agent.iteration",
                trace_id=trace_id,
                attributes={"iteration": iteration, "profile": profile_key},
            )
            try:
                result = await self.router.complete(
                    profile_name=profile_key,
                    profile=profile,
                    payload=payload,
                )
            except Exception as exc:
                self.trace_store.end_span(iter_span.span_id, status="error", error=str(exc))
                raise
            self.trace_store.end_span(
                iter_span.span_id,
                attributes={"escalated": result.escalated},
            )

            profile_key = result.profile_name
            profile = result.profile
            message = result.data["choices"][0]["message"]
            working.append(message)

            tool_calls = message.get("tool_calls") or []
            if not tool_calls or not tools_enabled:
                return AgentRunResult(
                    message=message,
                    profile_name=profile_key,
                    escalated=result.escalated,
                    retrieval_hits=retrieval_hits,
                    tool_calls=tool_names,
                    iterations=iteration + 1,
                )

            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
                tool_span = self.trace_store.start_span(
                    f"tool.{name}",
                    trace_id=trace_id,
                    attributes={"args": args},
                )
                output = self.tools.execute(name, args)
                tool_names.append(name)
                self.trace_store.end_span(tool_span.span_id, attributes={"tool": name})
                working.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "name": name,
                        "content": output,
                    }
                )

        final = working[-1]
        message = (
            final
            if isinstance(final, dict)
            else {"role": "assistant", "content": str(final)}
        )
        return AgentRunResult(
            message=message,
            profile_name=profile_key,
            escalated=False,
            retrieval_hits=retrieval_hits,
            tool_calls=tool_names,
            iterations=max_iters,
        )


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return str(message["content"])
    return ""


def _format_retrieval_context(chunks) -> str:
    parts = [
        "Relevant repository context (cite paths and line ranges when answering):",
    ]
    for chunk in chunks:
        parts.append(
            f"\n--- {chunk.path}:{chunk.start_line}-{chunk.end_line} ---\n{chunk.content}"
        )
    return "\n".join(parts)


def _prepend_system_context(
    messages: list[dict[str, Any]], context_block: str
) -> list[dict[str, Any]]:
    updated = [dict(m) for m in messages]
    if updated and updated[0].get("role") == "system":
        updated[0]["content"] = f"{updated[0]['content']}\n\n{context_block}"
    else:
        updated.insert(0, {"role": "system", "content": context_block})
    return updated
