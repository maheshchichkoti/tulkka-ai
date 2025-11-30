from __future__ import annotations
import time
import logging
from fastapi import Request
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from ..security import verify_jwt, JWTValidationError
from ..config import settings
from .errors import APIError

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT auth with public route support and dev-mode bypass."""

    PUBLIC_PATHS = {
        "/",
        "/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/process",
        "/v1/trigger-lesson-processing",
        "/v1/exercises",
    }

    # All games endpoints are intentionally public (no JWT required in this service)
    # Updated to match TULKKA Games APIs spec route prefixes
    GAMES_PUBLIC_PREFIXES = (
        "/v1/flashcards",
        "/v1/word-lists",
        "/v1/spelling",
        "/v1/grammar-challenge",
        "/v1/advanced-cloze",
        "/v1/sentence-builder",
    )

    def _is_public(self, path: str) -> bool:
        if path in self.PUBLIC_PATHS:
            return True
        for prefix in self.GAMES_PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
        return path.startswith("/docs") or path.startswith("/redoc")

    async def dispatch(self, request: Request, call_next):
        # Allow everything in development mode to unblock local testing
        if settings.ENVIRONMENT != "production":
            return await call_next(request)

        if self._is_public(request.url.path):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise APIError("UNAUTHORIZED", "missing bearer token", 401)

        token = auth.split(" ", 1)[1].strip()
        try:
            payload = verify_jwt(token)
            request.state.user = payload
        except JWTValidationError as exc:
            raise APIError("UNAUTHORIZED", str(exc), 401)

        return await call_next(request)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response: Response = await call_next(request)
        dur = int((time.time() - start) * 1000)
        logger.info("%s %s %d %dms", request.method, request.url.path, response.status_code, dur)
        return response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return await call_next(request)
        request.state.idempotency_key = key
        return await call_next(request)
