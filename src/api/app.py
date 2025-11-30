"""FastAPI application factory with production-ready configuration."""

from __future__ import annotations
import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .errors import APIError, api_error_handler, unhandled_handler
from .middlewares import JWTAuthMiddleware, RequestLogMiddleware, IdempotencyMiddleware
from .router_root import router as root_router
from .routes.lessons_routes import router as lessons_router
from ..games.routes.flashcards_routes import router as flashcards_router
from ..games.routes.spelling_routes import router as spelling_router
from ..games.routes.cloze_routes import router as cloze_router
from ..games.routes.grammar_routes import router as grammar_router
from ..games.routes.sentence_routes import router as sentence_router
from ..logging_config import configure_logging
from ..config import settings
# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup/shutdown."""
    # Startup
    from ..db.mysql_pool import AsyncMySQLPool
    await AsyncMySQLPool.init_pool()
    logging.info("Application started - environment: %s", settings.ENVIRONMENT)
    
    yield
    
    # Shutdown
    await AsyncMySQLPool.close_pool()
    logging.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    # Disable docs in production for security
    docs_url = None if settings.is_production() else "/docs"
    redoc_url = None if settings.is_production() else "/redoc"

    app = FastAPI(
        title="Tulkka AI",
        version="1.0.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan,
        description="AI-powered language learning exercise generation API",
    )
    
    # Attach rate limiter to app state
    app.state.limiter = limiter

    # CORS - production-safe configuration
    cors_origins = ["*"] if settings.CORS_ALLOW_ALL else settings.CORS_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Middlewares
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(JWTAuthMiddleware)

    # Routers
    app.include_router(root_router, prefix="/v1")
    app.include_router(lessons_router)
    app.include_router(flashcards_router)
    app.include_router(spelling_router)
    app.include_router(cloze_router)
    app.include_router(grammar_router)
    app.include_router(sentence_router)

    # Rate limit error handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Error handlers
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, unhandled_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle Pydantic validation errors with structured response."""
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors()
                }
            }
        )

    return app


app = create_app()
