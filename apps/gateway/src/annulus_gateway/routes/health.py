from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from annulus_gateway.deps import get_router, get_settings, verify_api_key

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health(
    model_router=Depends(get_router),
    settings=Depends(get_settings),
) -> dict[str, Any]:
    router_health = await model_router.health()
    return {
        "status": "ok",
        "service": "annulus-gateway",
        "version": "0.1.0",
        "trace_enabled": settings.trace.enabled,
        "default_profile": settings.router.default_profile,
        **router_health,
    }


@health_router.get("/health/ready")
async def readiness(
    _auth: None = Depends(verify_api_key),
    model_router=Depends(get_router),
) -> dict[str, Any]:
    router_health = await model_router.health()
    ollama_ok = router_health.get("ollama") == "ok"
    return {
        "ready": ollama_ok,
        **router_health,
    }
