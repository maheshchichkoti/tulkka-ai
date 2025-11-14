from __future__ import annotations
from fastapi import Request
from .errors import APIError

def get_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise APIError("UNAUTHORIZED", "missing user context", 401)
    return user
