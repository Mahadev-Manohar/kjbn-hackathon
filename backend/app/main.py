"""Application entry point: wiring only, no business rules."""

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from app.api.routers import crops, deliveries, farmers, health, payouts, price_list
from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Produce Procurement & Payout API",
        version="1.0.0",
        description=(
            "Farm produce buying centre: prices by crop, grade and date, moisture deductions, "
            "advance recovery and weekly payouts. Send the X-Test-Clock header to override "
            "the current date."
        ),
    )
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestContextMiddleware)

    api = APIRouter(prefix="/api/v1")
    for module in (farmers, crops, price_list, deliveries, payouts):
        api.include_router(module.router)
    app.include_router(api)
    app.include_router(health.router)

    logging.getLogger("app").info("app_started", extra={"env": settings.app_env})
    return app


app = create_app()
