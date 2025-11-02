"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_memory_layer import __version__
from ai_memory_layer.config import get_settings
from ai_memory_layer.database import init_engine
from ai_memory_layer.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_engine()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(api_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "ai_memory_layer.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    run()
