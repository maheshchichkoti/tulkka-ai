"""
Shared utilities for TULKKA Games APIs.
"""

from .responses import (
    ErrorCodes,
    ErrorResponse,
    Pagination,
    Progress,
    error_response,
    raise_error,
    paginate,
    apply_pagination,
    make_progress,
    ok_response,
    created_response,
    validate_page_limit,
    validate_ids_exist,
)

from .idempotency import (
    get_idempotency_key,
    check_idempotency,
    store_idempotency,
    check_client_result_id,
    cleanup_expired_keys,
)

__all__ = [
    # Responses
    "ErrorCodes",
    "ErrorResponse", 
    "Pagination",
    "Progress",
    "error_response",
    "raise_error",
    "paginate",
    "apply_pagination",
    "make_progress",
    "ok_response",
    "created_response",
    "validate_page_limit",
    "validate_ids_exist",
    # Idempotency
    "get_idempotency_key",
    "check_idempotency",
    "store_idempotency",
    "check_client_result_id",
    "cleanup_expired_keys",
]
