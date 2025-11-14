from __future__ import annotations
import time
import logging
from fastapi import Request
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from ..security import verify_jwt, JWTValidationError
from .errors import APIError

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
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
