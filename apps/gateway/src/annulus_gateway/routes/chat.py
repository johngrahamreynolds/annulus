from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from annulus_gateway.deps import get_router, get_settings, get_trace_store, verify_api_key

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
    model_router=Depends(get_router),
    trace_store=Depends(get_trace_store),
    settings=Depends(get_settings),
    _auth: None = Depends(verify_api_key),
):
    body: dict[str, Any] = await request.json()
    messages = body.get("messages", [])
    stream = bool(body.get("stream", False))
    requested_model = body.get("model")

    profile = model_router.resolve_profile(requested_model)
    if profile.provider != "ollama":
        raise HTTPException(
            status_code=501,
            detail=f"Provider '{profile.provider}' is not implemented in MVP passthrough.",
        )

    extra = {
        k: body.get(k)
        for k in ("temperature", "max_tokens", "top_p", "stop")
        if k in body
    }
    payload = model_router.build_payload(
        profile=profile,
        messages=messages,
        stream=stream,
        extra=extra,
    )

    span = trace_store.start_span(
        "chat.completions",
        attributes={
            "model": profile.model,
            "profile": requested_model or settings.router.default_profile,
            "stream": stream,
            "message_count": len(messages),
        },
    )

    try:
        if stream:
            return StreamingResponse(
                _stream_ollama(model_router, payload, span, trace_store),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Annulus-Trace-Id": span.trace_id,
                },
            )

        response = await model_router.ollama.chat_completions(payload)
        if response.status_code >= 400:
            trace_store.end_span(span.span_id, status="error", error=response.text)
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {"error": response.text},
                headers={"X-Annulus-Trace-Id": span.trace_id},
            )

        data = response.json()
        trace_store.end_span(
            span.span_id,
            status="ok",
            attributes={"response_id": data.get("id")},
        )
        return JSONResponse(content=data, headers={"X-Annulus-Trace-Id": span.trace_id})
    except HTTPException:
        trace_store.end_span(span.span_id, status="error", error="HTTPException")
        raise
    except Exception as exc:
        trace_store.end_span(span.span_id, status="error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Upstream Ollama error: {exc}") from exc


async def _stream_ollama(model_router, payload: dict[str, Any], span, trace_store):
    try:
        async for chunk in model_router.ollama.stream_chat_completions(payload):
            yield chunk
        trace_store.end_span(span.span_id, status="ok", attributes={"streamed": True})
    except Exception as exc:
        trace_store.end_span(span.span_id, status="error", error=str(exc))
        yield f'data: {{"error": "{str(exc)}"}}\n\n'.encode()
        yield b"data: [DONE]\n\n"
