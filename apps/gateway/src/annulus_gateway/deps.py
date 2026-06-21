from __future__ import annotations

from typing import Annotated

from annulus_core.config import AnnulusSettings, load_settings
from annulus_router.router import ModelRouter
from annulus_trace.store import TraceStore
from fastapi import Depends, Header, HTTPException

_settings: AnnulusSettings | None = None
_router: ModelRouter | None = None
_trace_store: TraceStore | None = None


def init_dependencies(settings: AnnulusSettings) -> None:
    global _settings, _router, _trace_store
    _settings = settings
    _router = ModelRouter(settings)
    _trace_store = TraceStore(settings.resolve_trace_db())


async def shutdown_dependencies() -> None:
    if _router is not None:
        await _router.close()


def get_settings() -> AnnulusSettings:
    if _settings is None:
        return load_settings()
    return _settings


def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter(get_settings())
    return _router


def get_trace_store() -> TraceStore:
    global _trace_store
    if _trace_store is None:
        _trace_store = TraceStore(get_settings().resolve_trace_db())
    return _trace_store


def verify_api_key(
    settings: Annotated[AnnulusSettings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Validate bearer token or X-API-Key against configured gateway key."""
    expected = settings.gateway.api_key
    if not expected:
        return

    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_api_key:
        token = x_api_key.strip()

    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
