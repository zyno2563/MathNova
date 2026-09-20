"""MathNova API — FastAPI application factory and entry point."""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import settings
from backend.errors import EngineError, sanitize
from backend.limits import BodySizeLimitMiddleware
from backend.security_headers import SecurityHeadersMiddleware
from backend.routers import (
    assistant,
    calculus,
    fourier,
    linear_algebra,
    numerical,
    ode,
    pde,
    transforms,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend"
)


def create_app():
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version=settings.APP_VERSION,
        description=(
            "REST interface to the MathNova engineering-mathematics "
            "engines: Fourier series, calculus, linear algebra, ODEs, "
            "PDEs, numerical methods, and transforms."
        ),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json"
    )

    # Outermost, so even an error response carries the headers.
    app.add_middleware(SecurityHeadersMiddleware)

    # Refuse oversized bodies before anything reads them.
    app.add_middleware(BodySizeLimitMiddleware)

    origins = settings.cors_origins

    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            # Never true. The API holds no session and reads no cookie,
            # so credentialed cross-origin requests have nothing to
            # carry — and allow_credentials with a wildcard origin is
            # the classic way to make an API readable by any site.
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
            max_age=600
        )

    # ---------------------------------------------------------
    # Error contract
    # ---------------------------------------------------------

    @app.exception_handler(EngineError)
    async def handle_engine_error(request: Request, error: EngineError):
        return JSONResponse(
            status_code=error.status_code,
            content={
                "ok": False,
                "error": {"code": error.code, "message": error.message}
            }
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ):
        problems = []

        for item in error.errors():
            location = ".".join(
                str(part) for part in item.get("loc", ())
                if part not in ("body",)
            )
            detail = sanitize(item.get("msg", "invalid value"))

            problems.append(f"{location}: {detail}" if location else detail)

        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "error": {
                    "code": "validation_error",
                    "message": "; ".join(problems) or "Invalid request body"
                }
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, error: StarletteHTTPException
    ):
        # Keeps 404/405 on the same envelope as everything else, but
        # only for the API surface — static file requests should still
        # get a plain response.
        if not request.url.path.startswith("/api"):
            return JSONResponse(
                status_code=error.status_code,
                content={"detail": error.detail}
            )

        codes = {404: "not_found", 405: "method_not_allowed"}

        return JSONResponse(
            status_code=error.status_code,
            content={
                "ok": False,
                "error": {
                    "code": codes.get(error.status_code, "http_error"),
                    "message": sanitize(error.detail)
                }
            }
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception):
        # Logged in full server-side; the client is told nothing about
        # the internals. This does not soften in DEBUG — a debug flag
        # left on in production must not start leaking tracebacks.
        logging.getLogger("mathnova").exception(
            "Unhandled error on %s", request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "internal_error",
                    "message": "Unexpected server error."
                }
            }
        )

    # ---------------------------------------------------------
    # Routes
    # ---------------------------------------------------------

    @app.get("/api/health", tags=["meta"])
    def health():
        return {
            "ok": True,
            "result": {
                "status": "healthy",
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "assistant_enabled": settings.assistant_enabled,
                "modules": [
                    "fourier-series",
                    "calculus",
                    "linear-algebra",
                    "ode",
                    "pde",
                    "numerical",
                    "transforms",
                    "assistant"
                ]
            }
        }

    for router in (
        fourier.router,
        calculus.router,
        linear_algebra.router,
        ode.router,
        pde.router,
        numerical.router,
        transforms.router,
        assistant.router,
    ):
        app.include_router(router, prefix="/api")

    # Registered after the real routers but before the static mount,
    # so an unmatched /api path 404s instead of falling through to the
    # file server (which would answer 405 for a POST).
    @app.api_route(
        "/api/{rest:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False
    )
    def api_not_found(rest: str):
        raise EngineError(404, "not_found", f"No API endpoint at /api/{rest}")

    # ---------------------------------------------------------
    # Frontend (mounted last so /api/* always wins)
    # ---------------------------------------------------------

    if os.path.isdir(FRONTEND_DIR):

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

        app.mount(
            "/",
            StaticFiles(directory=FRONTEND_DIR, html=True),
            name="frontend"
        )

    return app


app = create_app()
