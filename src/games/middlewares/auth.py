# src/middlewares/auth.py
from fastapi import Header
from typing import Optional

def get_current_user(x_user_id: Optional[str] = Header(None, alias="X-User-Id")):
    """Lightweight, non-authenticated user resolver for games APIs.

    - If X-User-Id header is provided, use it directly as userId (no JWT validation).
    - Otherwise fall back to a fixed anonymous user id.
    """

    if x_user_id:
        return {"userId": x_user_id, "claims": {}}

    # Fallback anonymous user (no authentication enforced in this service)
    return {"userId": "anonymous-user", "claims": {}}
