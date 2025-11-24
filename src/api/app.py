from __future__ import annotations
import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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

def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="Tulkka AI", version="1.0.0", docs_url="/docs", redoc_url="/redoc")

    # Startup/shutdown events
    @app.on_event("startup")
    async def startup():
        from ..db.mysql_pool import AsyncMySQLPool
        await AsyncMySQLPool.init_pool()
        logging.info("Application started")

    @app.on_event("shutdown")
    async def shutdown():
        from ..db.mysql_pool import AsyncMySQLPool
        await AsyncMySQLPool.close_pool()
        logging.info("Application shutdown")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
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

    # Error handlers
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, unhandled_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request, exc):
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Invalid request", "details": exc.errors()}}
        )

    return app

app = create_app()
