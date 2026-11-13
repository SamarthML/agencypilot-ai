"""FastAPI application factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import copilot, health, insights, reports, seo, usage
from app.core.config import Settings, apply_runtime_env, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

FEATURE_ROUTERS = (insights.router, seo.router, copilot.router, reports.router, usage.router)


def add_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-LLM-Provider"],
    )


def create_app() -> FastAPI:
    settings = get_settings()
    apply_runtime_env(settings)

    app = FastAPI(title=settings.app_name, version=settings.version)
    add_cors(app, settings)
    app.include_router(health.router)
    for router in FEATURE_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
