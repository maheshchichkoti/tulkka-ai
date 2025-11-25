# src/security.py
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from .config import settings
import logging

logger = logging.getLogger(__name__)

class JWTValidationError(Exception):
    """JWT validation error"""
    pass

def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token. Returns payload or None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET or "", algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.debug("JWT decode failed: %s", e)
        return None

def verify_jwt(token: str) -> Dict[str, Any]:
    """Verify JWT and return payload, raise JWTValidationError if invalid"""
    if not token:
        raise JWTValidationError("Missing token")
    if not settings.JWT_SECRET:
        logger.error("JWT_SECRET not configured - rejecting all tokens in production")
        raise JWTValidationError("Server misconfigured: JWT_SECRET not set")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTValidationError(f"Invalid token: {e}")

def require_scope(payload: Dict[str, Any], required_scope: str) -> bool:
    """Check scope presence in token payload (simple)."""
    if not payload:
        return False
    scopes = payload.get("scope") or payload.get("scopes") or payload.get("permissions") or []
    if isinstance(scopes, str):
        scopes = scopes.split()
    return required_scope in scopes
