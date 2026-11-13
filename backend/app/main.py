"""FastAPI application factory."""

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import copilot, health, insights, models, reports, seo, usage
from app.core.config import Settings, apply_runtime_env, get_settings
from app.services import copilot as copilot_service
from app.services.analytics import CsvValidationError
from app.services.copilot import (
    DocumentNotFoundError,
    InvalidDocumentError,
    UnsupportedDocumentError,
)
from app.services.insights import DatasetNotFoundError
from app.services.llm import (
    LLMError,
    LLMOutputError,
    ProviderNotConfiguredError,
    ProviderUnavailableError,
)
from app.services.reports import ReportNotFoundError
from app.services.seo.fetcher import (
    BlockedAddressError,
    FetchTimeoutError,
    InvalidUrlError,
    NotHtmlError,
    PageTooLargeError,
    SeoFetchError,
    SiteBlocksBotsError,
    SiteUnreachableError,
)
from app.services.seo_audit import SeoAuditNotFoundError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

FEATURE_ROUTERS = (
    models.router,
    insights.router,
    seo.router,
    copilot.router,
    reports.router,
    usage.router,
)

# Service-layer errors carry a user-facing message; this maps them to HTTP status codes so
# routes stay thin and services stay HTTP-agnostic.
DOMAIN_ERROR_STATUS: dict[type[Exception], int] = {
    ProviderNotConfiguredError: status.HTTP_400_BAD_REQUEST,
    ProviderUnavailableError: status.HTTP_502_BAD_GATEWAY,
    LLMOutputError: status.HTTP_502_BAD_GATEWAY,
    LLMError: status.HTTP_502_BAD_GATEWAY,
    CsvValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    DatasetNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidUrlError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    BlockedAddressError: status.HTTP_400_BAD_REQUEST,
    FetchTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
    NotHtmlError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    PageTooLargeError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    SiteBlocksBotsError: status.HTTP_502_BAD_GATEWAY,
    SiteUnreachableError: status.HTTP_502_BAD_GATEWAY,
    SeoFetchError: status.HTTP_502_BAD_GATEWAY,
    SeoAuditNotFoundError: status.HTTP_404_NOT_FOUND,
    DocumentNotFoundError: status.HTTP_404_NOT_FOUND,
    UnsupportedDocumentError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    InvalidDocumentError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ReportNotFoundError: status.HTTP_404_NOT_FOUND,
}
HANDLED_ERRORS = (
    LLMError,
    CsvValidationError,
    DatasetNotFoundError,
    SeoFetchError,
    SeoAuditNotFoundError,
    DocumentNotFoundError,
    UnsupportedDocumentError,
    InvalidDocumentError,
    ReportNotFoundError,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # The embedding model takes ~30-60 s to import and load; doing it in a daemon thread keeps
    # startup instant while making sure the first chat request doesn't pay for it.
    if get_settings().copilot_warmup:
        threading.Thread(target=copilot_service.warm_up, name="copilot-warmup", daemon=True).start()
    yield


def add_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Content-Disposition carries the report PDF filename to the browser download.
        expose_headers=["X-LLM-Provider", "Content-Disposition"],
    )


async def handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    code = next(
        (DOMAIN_ERROR_STATUS[cls] for cls in type(exc).__mro__ if cls in DOMAIN_ERROR_STATUS),
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=code, content={"detail": str(exc)})


def create_app() -> FastAPI:
    settings = get_settings()
    apply_runtime_env(settings)

    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
    add_cors(app, settings)
    for error_type in HANDLED_ERRORS:
        app.add_exception_handler(error_type, handle_domain_error)
    app.include_router(health.router)
    for router in FEATURE_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
