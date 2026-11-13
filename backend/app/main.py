"""FastAPI application factory."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import copilot, health, insights, models, reports, seo, usage
from app.core.config import Settings, apply_runtime_env, get_settings
from app.services.llm import (
    LLMError,
    LLMOutputError,
    ProviderNotConfiguredError,
    ProviderUnavailableError,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

FEATURE_ROUTERS = (
    models.router,
    insights.router,
    seo.router,
    copilot.router,
    reports.router,
    usage.router,
)

LLM_ERROR_STATUS: dict[type[LLMError], int] = {
    ProviderNotConfiguredError: status.HTTP_400_BAD_REQUEST,
    ProviderUnavailableError: status.HTTP_502_BAD_GATEWAY,
    LLMOutputError: status.HTTP_502_BAD_GATEWAY,
}


def add_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-LLM-Provider"],
    )


async def handle_llm_error(_: Request, exc: Exception) -> JSONResponse:
    code = LLM_ERROR_STATUS.get(type(exc), status.HTTP_502_BAD_GATEWAY)
    return JSONResponse(status_code=code, content={"detail": str(exc)})


def create_app() -> FastAPI:
    settings = get_settings()
    apply_runtime_env(settings)

    app = FastAPI(title=settings.app_name, version=settings.version)
    add_cors(app, settings)
    app.add_exception_handler(LLMError, handle_llm_error)
    app.include_router(health.router)
    for router in FEATURE_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
