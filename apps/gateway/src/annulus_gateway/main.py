from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from annulus_core.config import load_settings
from fastapi import FastAPI

from annulus_gateway.deps import init_dependencies, shutdown_dependencies
from annulus_gateway.routes.chat import chat_router
from annulus_gateway.routes.health import health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    init_dependencies(settings)
    yield
    await shutdown_dependencies()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Annulus Gateway",
        description="OpenAI-compatible gateway for local-first agentic AI",
        version="0.1.0",
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
