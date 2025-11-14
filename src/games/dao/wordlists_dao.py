from __future__ import annotations
from typing import List, Optional
from src.db.mysql_pool import execute_query
from src.time_utils import utc_now_iso


async def get_wordlists(user_id: str, search: str, favorite: Optional[bool], page: int, limit: int):
    base = "SELECT * FROM word_lists WHERE user_id=%s"
    params = [user_id]

    if search:
        base += " AND name LIKE %s"
        params.append(f"%{search}%")

    if favorite is not None:
        base += " AND is_favorite=%s"
        params.append(favorite)

    base += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, (page - 1) * limit])

    rows = await execute_query(base, tuple(params), fetchall=True)
    return rows


async def get_wordlist_by_id(list_id: str, user_id: str):
    q = "SELECT * FROM word_lists WHERE id=%s AND user_id=%s"
    return await execute_query(q, (list_id, user_id), fetchone=True)


async def create_wordlist(user_id: str, name: str, description: str):
    q = """
    INSERT INTO word_lists(id, user_id, name, description, is_favorite, word_count, created_at, updated_at)
    VALUES(UUID(), %s, %s, %s, FALSE, 0, %s, %s)
    """
    now = utc_now_iso()
    await execute_query(q, (user_id, name, description, now, now))
    q2 = "SELECT * FROM word_lists WHERE user_id=%s AND name=%s ORDER BY created_at DESC LIMIT 1"
    return await execute_query(q2, (user_id, name), fetchone=True)


async def update_wordlist(list_id: str, user_id: str, payload: dict):
    sets = []
    params = []
    for k, v in payload.items():
        sets.append(f"{k}=%s")
        params.append(v)
    params.extend([list_id, user_id])

    q = f"UPDATE word_lists SET {', '.join(sets)}, updated_at=%s WHERE id=%s AND user_id=%s"
    params.insert(-2, utc_now_iso())
    await execute_query(q, tuple(params))
    return await get_wordlist_by_id(list_id, user_id)


async def delete_wordlist(list_id: str, user_id: str):
    q = "DELETE FROM word_lists WHERE id=%s AND user_id=%s"
    await execute_query(q, (list_id, user_id))
