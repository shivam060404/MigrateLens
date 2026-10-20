"""HTTP composition; routes translate transport contracts into application operations."""

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src import __version__
from src.api.routes.health import router as health_router
from src.config.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="MigrateLens control API",
        version=__version__,
        description="Local reference foundation. Customer execution and publication disabled.",
    )
    app.state.settings = settings
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "backend", "testserver"]
    )
    app.include_router(health_router, prefix="/api/v1")
    return app
