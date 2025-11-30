"""Standardized API response helpers."""

from __future__ import annotations
from typing import Any, Dict, Optional, List


def success(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Create a successful response payload."""
    response: Dict[str, Any] = {"success": True, "data": data}
    if message:
        response["message"] = message
    return response


def error(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an error response payload."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }


def paginated(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """Create a paginated response payload."""
    return {
        "success": True,
        "data": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
        }
    }
