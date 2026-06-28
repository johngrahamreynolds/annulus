from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from annulus_gateway.deps import get_runtime, get_settings, get_trace_store, verify_api_key

chat_router = APIRouter(prefix="/v1", tags=["openai"])


@chat_router.get("/models")
async def list_models(
    settings=Depends(get_settings),
    _auth: None = Depends(verify_api_key),
) -> dict[str, Any]:
    models = []
    for name, profile in settings.models.profiles.items():
        models.append(
            {
                "id": name,
                "object": "model",
                "owned_by": profile.provider,
            }
        )
    return {"object": "list", "data": models}


@chat_router.post("/chat/completions")
async def chat_completions(
    request: Request,
    runtime=Depends(get_runtime),
    trace_store=Depends(get_trace_store),
    settings=Depends(get_settings),
    _auth: None = Depends(verify_api_key),
):
    body: dict[str, Any] = await request.json()
    messages = body.get("messages", [])
    stream = bool(body.get("stream", False))
    requested_model = body.get("model")

    extra = {
        k: body.get(k)
        for k in ("temperature", "max_tokens", "top_p", "stop")
        if k in body
    }

    span = trace_store.start_span(
        "chat.completions",
        attributes={
            "profile": requested_model or settings.router.default_profile,
            "stream": stream,
            "message_count": len(messages),
        },
    )

    try:
        if stream:
            return StreamingResponse(
                _stream_chat(
                    runtime=runtime,
                    messages=messages,
                    profile_name=requested_model,
                    trace_id=span.trace_id,
                    extra=extra,
                    span=span,
                    trace_store=trace_store,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Annulus-Trace-Id": span.trace_id,
                },
            )

        result = await runtime.run(
            messages=messages,
            profile_name=requested_model,
            trace_id=span.trace_id,
            extra=extra,
        )

        response_body = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": result.profile_name,
            "choices": [
                {
                    "index": 0,
                    "message": result.message,
                    "finish_reason": "stop",
                }
            ],
            "annulus": {
                "escalated": result.escalated,
                "retrieval_hits": result.retrieval_hits,
                "tool_calls": result.tool_calls,
                "iterations": result.iterations,
            },
        }
        trace_store.end_span(
            span.span_id,
            status="ok",
            attributes={
                "escalated": result.escalated,
                "iterations": result.iterations,
                "tools": result.tool_calls,
            },
        )
        return JSONResponse(
            content=response_body,
            headers={"X-Annulus-Trace-Id": span.trace_id},
        )
    except HTTPException:
        trace_store.end_span(span.span_id, status="error", error="HTTPException")
        raise
    except Exception as exc:
        trace_store.end_span(span.span_id, status="error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Agent runtime error: {exc}") from exc


async def _stream_chat(
    *,
    runtime,
    messages,
    profile_name,
    trace_id,
    extra,
    span,
    trace_store,
):
    try:
        async for chunk in runtime.stream_run(
            messages=messages,
            profile_name=profile_name,
            trace_id=trace_id,
            extra=extra,
        ):
            yield chunk
        trace_store.end_span(span.span_id, status="ok", attributes={"streamed": True})
    except Exception as exc:
        trace_store.end_span(span.span_id, status="error", error=str(exc))
        yield f"data: {json.dumps({'error': str(exc)})}\n\n".encode()
        yield b"data: [DONE]\n\n"
