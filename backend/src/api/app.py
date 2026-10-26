"""HTTP composition; routes translate transport contracts into application operations."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src import __version__
from src.api.routes.health import router as health_router
from src.config.settings import Settings
from src.bootstrap import create_control_plane
from src.api.routes.control import router as control_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            engine = getattr(app.state, "control_engine", None)
            if engine is not None:
                engine.dispose()

    app = FastAPI(
        title="MigrateLens control API",
        version=__version__,
        description="Local reference foundation. Customer execution and publication disabled.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "backend", "testserver"]
    )
    app.include_router(health_router, prefix="/api/v1")

    @app.middleware("http")
    async def private_control_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/tenants/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    if settings.control_api_enabled:
        service, verifier, engine = create_control_plane(settings)
        app.state.control_service = service
        app.state.token_verifier = verifier
        app.state.control_engine = engine
        app.include_router(control_router, prefix="/api/v1")
    return app
