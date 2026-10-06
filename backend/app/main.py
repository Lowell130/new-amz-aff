"""Entry point FastAPI.

Avvio sviluppo:  uvicorn app.main:app --reload
Documentazione:  http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import configurator, finder, misc
from app.core.config import Settings, get_settings
from app.core.container import build_container
from app.repositories.base import Repositories


def create_app(settings: Settings | None = None, repos: Repositories | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = await build_container(settings, repos)
        yield
        await app.state.container.close()

    app = FastAPI(
        title="Product Discovery Engine",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.app_env == "production" else "/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(misc.router)
    app.include_router(finder.router)
    app.include_router(configurator.router)
    return app


app = create_app()
