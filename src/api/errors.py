"""API error handling utilities."""

from __future__ import annotations
import logging
import traceback
from typing import Optional, Dict, Any

from fastapi import Request
from fastapi.responses import JSONResponse

from ..config import settings

logger = logging.getLogger(__name__)


class APIError(Exception):
    """
    Custom API exception with structured error response.
    
    Args:
        code: Error code (e.g., 'VALIDATION_ERROR', 'NOT_FOUND')
        message: Human-readable error message
        status: HTTP status code (default: 400)
        details: Additional error details
    """
    
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found",
            status=404,
            details={"resource": resource, "identifier": str(identifier)}
        )


class ValidationError(APIError):
    """Request validation error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status=422,
            details=details
        )


class UnauthorizedError(APIError):
    """Authentication required error."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status=401
        )


class ForbiddenError(APIError):
    """Permission denied error."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status=403
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions with structured response."""
    logger.warning(
        "API error: code=%s, status=%d, message=%s, path=%s",
        exc.code, exc.status, exc.message, request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with safe error response."""
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    
    # Include stack trace in development only
    details: Dict[str, Any] = {}
    if not settings.is_production():
        details["traceback"] = traceback.format_exc()
        details["exception_type"] = type(exc).__name__
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": details
            }
        }
    )
