"""FastAPI dependency injection utilities."""

from __future__ import annotations
from typing import Dict, Any, Optional

from fastapi import Request, Depends

from .errors import APIError


def get_user(request: Request) -> Dict[str, Any]:
    """
    Get the authenticated user from request state.
    
    Raises:
        APIError: If user is not authenticated
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise APIError("UNAUTHORIZED", "Authentication required", 401)
    return user


def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get the authenticated user if present, otherwise None."""
    return getattr(request.state, "user", None)


def get_request_id(request: Request) -> Optional[str]:
    """Get the request ID from headers or state."""
    return (
        request.headers.get("X-Request-ID") or
        getattr(request.state, "request_id", None)
    )


def get_idempotency_key(request: Request) -> Optional[str]:
    """Get the idempotency key from request state."""
    return getattr(request.state, "idempotency_key", None)
