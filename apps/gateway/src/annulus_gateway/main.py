from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from annulus_core.config import load_settings
from annulus_retrieval.indexer import Indexer
from fastapi import FastAPI

from annulus_gateway.deps import init_dependencies, shutdown_dependencies
from annulus_gateway.routes.chat import chat_router
from annulus_gateway.routes.health import health_router


async def _index_watch_loop(settings, stop: asyncio.Event) -> None:
    indexer = Indexer(settings)
    interval = settings.retrieval.index_watch_interval_seconds
    while not stop.is_set():
        await asyncio.to_thread(indexer.index_incremental)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    init_dependencies(settings)
    stop = asyncio.Event()
    watch_task: asyncio.Task[None] | None = None
    if settings.agent.index_watch_enabled:
        watch_task = asyncio.create_task(_index_watch_loop(settings, stop))
    yield
    stop.set()
    if watch_task is not None:
        await watch_task
    await shutdown_dependencies()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Annulus Gateway",
        description="OpenAI-compatible gateway with retrieval and tools",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(chat_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "annulus_gateway.main:app",
        host=settings.gateway.host,
        port=settings.gateway.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
