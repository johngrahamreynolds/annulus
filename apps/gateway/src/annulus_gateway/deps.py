from __future__ import annotations

from typing import Annotated

from annulus_core.config import AnnulusSettings, load_settings
from annulus_retrieval.retriever import Retriever
from annulus_router.router import ModelRouter
from annulus_runtime.agent import AgentRuntime
from annulus_tools.executor import ToolExecutor
from annulus_trace.store import TraceStore
from fastapi import Depends, Header, HTTPException

_settings: AnnulusSettings | None = None
_router: ModelRouter | None = None
_trace_store: TraceStore | None = None
_retriever: Retriever | None = None
_tools: ToolExecutor | None = None
_runtime: AgentRuntime | None = None


def init_dependencies(settings: AnnulusSettings) -> None:
    global _settings, _router, _trace_store, _retriever, _tools, _runtime
    _settings = settings
    _router = ModelRouter(settings)
    _trace_store = TraceStore(settings.resolve_trace_db())
    _retriever = Retriever(settings)
    _tools = ToolExecutor(settings)
    _runtime = AgentRuntime(settings, _router, _retriever, _tools, _trace_store)


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


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(get_settings())
    return _retriever


def get_runtime() -> AgentRuntime:
    global _runtime
    if _runtime is None:
        settings = get_settings()
        _runtime = AgentRuntime(
            settings,
            get_router(),
            get_retriever(),
            ToolExecutor(settings),
            get_trace_store(),
        )
    return _runtime


def verify_api_key(
    settings: Annotated[AnnulusSettings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
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
