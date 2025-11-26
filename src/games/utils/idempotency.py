"""
Idempotency support for TULKKA Games APIs.
Handles Idempotency-Key header and clientResultId deduplication.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from fastapi import Request


async def get_idempotency_key(request: Request) -> Optional[str]:
    """Extract Idempotency-Key header from request."""
    return request.headers.get("Idempotency-Key")


async def check_idempotency(
    pool,
    user_id: str,
    endpoint: str,
    idempotency_key: str
) -> Optional[Dict[str, Any]]:
    """
    Check if an idempotency key has been used before.
    Returns the cached response if found, None otherwise.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT response_data FROM idempotency_keys
                WHERE user_id = %s AND endpoint = %s AND idempotency_key = %s
                AND (expires_at IS NULL OR expires_at > NOW())
                """,
                (user_id, endpoint, idempotency_key)
            )
            row = await cur.fetchone()
            if row and row[0]:
                return json.loads(row[0]) if isinstance(row[0], str) else row[0]
    return None


async def store_idempotency(
    pool,
    user_id: str,
    endpoint: str,
    idempotency_key: str,
    response_data: Dict[str, Any],
    ttl_hours: int = 24
) -> None:
    """Store an idempotency key with its response for future deduplication."""
    key_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO idempotency_keys (id, user_id, endpoint, idempotency_key, response_data, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE response_data = VALUES(response_data), expires_at = VALUES(expires_at)
                """,
                (key_id, user_id, endpoint, idempotency_key, json.dumps(response_data), expires_at)
            )
            await conn.commit()


async def check_client_result_id(
    pool,
    session_id: str,
    client_result_id: str
) -> Optional[Dict[str, Any]]:
    """
    Check if a clientResultId has been used in this session.
    Returns the existing result if found.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, is_correct, attempts, time_spent_ms, created_at
                FROM game_results
                WHERE session_id = %s AND client_result_id = %s
                """,
                (session_id, client_result_id)
            )
            row = await cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "isCorrect": bool(row[1]),
                    "attempts": row[2],
                    "timeSpentMs": row[3],
                    "createdAt": row[4].isoformat() + "Z" if row[4] else None
                }
    return None


async def cleanup_expired_keys(pool) -> int:
    """Remove expired idempotency keys. Returns count of deleted rows."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM idempotency_keys WHERE expires_at < NOW()"
            )
            await conn.commit()
            return cur.rowcount
