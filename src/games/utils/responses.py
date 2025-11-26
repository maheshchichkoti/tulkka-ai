"""
Shared response utilities for TULKKA Games APIs.
Provides standardized error shapes, pagination, and response helpers.
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel
from fastapi import HTTPException
from fastapi.responses import JSONResponse


# =============================================================================
# Standard Error Shape (per spec)
# =============================================================================

class ErrorDetails(BaseModel):
    """Optional error details."""
    invalidIds: Optional[List[str]] = None
    field: Optional[str] = None
    reason: Optional[str] = None


class ErrorBody(BaseModel):
    """Standard error body per spec."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""
    error: ErrorBody


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details
            }
        }
    )


def raise_error(
    status_code: int,
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
):
    """Raise an HTTPException with standardized error format."""
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": details
        }
    )


# Common error codes
class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN_WORD = "UNKNOWN_WORD"
    UNKNOWN_ITEM = "UNKNOWN_ITEM"
    UNKNOWN_QUESTION = "UNKNOWN_QUESTION"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    WORD_LIST_NOT_FOUND = "WORD_LIST_NOT_FOUND"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# =============================================================================
# Pagination (per spec)
# =============================================================================

class Pagination(BaseModel):
    """Pagination metadata."""
    page: int
    limit: int
    total: int


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    data: List[Any]
    pagination: Pagination


def paginate(
    items: List[Any],
    page: int = 1,
    limit: int = 20,
    total: Optional[int] = None
) -> Dict[str, Any]:
    """Create a paginated response."""
    actual_total = total if total is not None else len(items)
    return {
        "data": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": actual_total
        }
    }


def apply_pagination(
    items: List[Any],
    page: int = 1,
    limit: int = 20
) -> tuple[List[Any], int]:
    """Apply pagination to a list and return (paginated_items, total)."""
    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    return items[start:end], total


# =============================================================================
# Progress Object (shared across all games)
# =============================================================================

class Progress(BaseModel):
    """Session progress tracking."""
    current: int
    total: int
    correct: int
    incorrect: int


def make_progress(current: int, total: int, correct: int, incorrect: int) -> Dict[str, int]:
    """Create a progress object."""
    return {
        "current": current,
        "total": total,
        "correct": correct,
        "incorrect": incorrect
    }


# =============================================================================
# Success Responses
# =============================================================================

def ok_response(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Simple OK response."""
    response = {"ok": True}
    if data:
        response.update(data)
    return response


def created_response(data: Dict[str, Any], location: Optional[str] = None) -> JSONResponse:
    """201 Created response with optional Location header."""
    headers = {}
    if location:
        headers["Location"] = location
    return JSONResponse(
        status_code=201,
        content=data,
        headers=headers if headers else None
    )


# =============================================================================
# Validation Helpers
# =============================================================================

def validate_page_limit(page: int, limit: int, max_limit: int = 100):
    """Validate pagination parameters."""
    if page < 1:
        raise_error(400, ErrorCodes.VALIDATION_ERROR, "page must be >= 1")
    if limit < 1 or limit > max_limit:
        raise_error(400, ErrorCodes.VALIDATION_ERROR, f"limit must be between 1 and {max_limit}")


def validate_ids_exist(
    requested_ids: List[str],
    existing_ids: List[str],
    error_code: str = ErrorCodes.UNKNOWN_ITEM,
    item_type: str = "item"
) -> None:
    """Validate that all requested IDs exist."""
    existing_set = set(existing_ids)
    invalid_ids = [id for id in requested_ids if id not in existing_set]
    if invalid_ids:
        raise_error(
            400,
            error_code,
            f"Unknown {item_type} IDs",
            {"invalidIds": invalid_ids}
        )
