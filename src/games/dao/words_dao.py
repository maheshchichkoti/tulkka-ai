from __future__ import annotations
from typing import List
from src.db.mysql_pool import execute_query
from src.time_utils import utc_now_iso


async def get_words_by_list(list_id: str, limit: int = 100, offset: int = 0):
    q = "SELECT * FROM words WHERE list_id=%s ORDER BY created_at ASC LIMIT %s OFFSET %s"
    return await execute_query(q, (list_id, limit, offset), fetchall=True)


async def get_word(word_id: str, list_id: str):
    q = "SELECT * FROM words WHERE id=%s AND list_id=%s"
    return await execute_query(q, (word_id, list_id), fetchone=True)


async def create_word(list_id: str, word: str, translation: str, notes: str = None, difficulty: str = 'beginner'):
    now = utc_now_iso()
    q = """
    INSERT INTO words(
        id, list_id, word, translation, notes, difficulty,
        is_favorite, practice_count, correct_count,
        accuracy, last_practiced, created_at, updated_at
    ) VALUES(UUID(), %s, %s, %s, %s, %s, FALSE, 0, 0, 0, NULL, %s, %s)
    """
    await execute_query(q, (list_id, word, translation, notes, difficulty, now, now))

    q2 = "SELECT * FROM words WHERE list_id=%s ORDER BY created_at DESC LIMIT 1"
    return await execute_query(q2, (list_id,), fetchone=True)


async def update_word(word_id: str, list_id: str, payload: dict):
    sets = []
    params = []
    for k, v in payload.items():
        sets.append(f"{k}=%s")
        params.append(v)

    params.extend([word_id, list_id])

    q = f"""
    UPDATE words SET {', '.join(sets)}, updated_at=%s
    WHERE id=%s AND list_id=%s
    """
    params.insert(-2, utc_now_iso())
    await execute_query(q, tuple(params))
    return await get_word(word_id, list_id)


async def delete_word(word_id: str, list_id: str):
    q = "DELETE FROM words WHERE id=%s AND list_id=%s"
    await execute_query(q, (word_id, list_id))
