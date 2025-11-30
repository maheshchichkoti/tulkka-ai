# src/security.py
"""Security utilities for JWT authentication and authorization."""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import logging
import hashlib
import secrets

from jose import jwt, JWTError

from .config import settings

logger = logging.getLogger(__name__)


class JWTValidationError(Exception):
    """Raised when JWT validation fails."""
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
    """Check scope presence in token payload."""
    if not payload:
        return False
    scopes = payload.get("scope") or payload.get("scopes") or payload.get("permissions") or []
    if isinstance(scopes, str):
        scopes = scopes.split()
    return required_scope in scopes


def require_any_scope(payload: Dict[str, Any], required_scopes: List[str]) -> bool:
    """Check if any of the required scopes are present."""
    if not payload or not required_scopes:
        return False
    scopes = payload.get("scope") or payload.get("scopes") or payload.get("permissions") or []
    if isinstance(scopes, str):
        scopes = scopes.split()
    return any(scope in scopes for scope in required_scopes)


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return secrets.compare_digest(hash_api_key(api_key), hashed_key)
