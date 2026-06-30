from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from annulus_gateway.deps import get_retriever, get_router, get_settings, verify_api_key

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health(
    model_router=Depends(get_router),
    settings=Depends(get_settings),
    retriever=Depends(get_retriever),
) -> dict[str, Any]:
    router_health = await model_router.health()
    index_stats = retriever.stats()
    return {
        "status": "ok",
        "service": "annulus-gateway",
        "version": "0.2.0",
        "trace_enabled": settings.trace.enabled,
        "retrieval_enabled": settings.agent.retrieval_enabled,
        "tools_enabled": settings.agent.tools_enabled,
        "default_profile": settings.router.default_profile,
        "index": index_stats,
        **router_health,
    }


@health_router.get("/health/ready")
async def readiness(
    _auth: None = Depends(verify_api_key),
    model_router=Depends(get_router),
    retriever=Depends(get_retriever),
) -> dict[str, Any]:
    router_health = await model_router.health()
    ollama_ok = router_health.get("ollama") == "ok"
    openai_ok = router_health.get("ollama_openai_compat") in (None, "ok")
    index_stats = retriever.stats()
    return {
        "ready": ollama_ok and openai_ok,
        "index_chunks": index_stats.get("chunks", 0),
        **router_health,
    }
