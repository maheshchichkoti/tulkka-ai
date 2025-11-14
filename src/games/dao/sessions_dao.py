from __future__ import annotations
from src.db.mysql_pool import execute_query
from src.time_utils import utc_now_iso


async def create_session(user_id: str, list_id: str, total: int):
    q = """
    INSERT INTO flashcard_sessions(
        id, user_id, list_id, progress_current,
        progress_total, correct, incorrect,
        started_at, completed_at
    ) VALUES(UUID(), %s, %s, 0, %s, 0, 0, %s, NULL)
    """
    now = utc_now_iso()
    await execute_query(q, (user_id, list_id, total, now))

    q2 = "SELECT * FROM flashcard_sessions WHERE user_id=%s AND list_id=%s ORDER BY started_at DESC LIMIT 1"
    return await execute_query(q2, (user_id, list_id), fetchone=True)


async def get_session(session_id: str, user_id: str):
    q = "SELECT * FROM flashcard_sessions WHERE id=%s AND user_id=%s"
    return await execute_query(q, (session_id, user_id), fetchone=True)


async def update_progress(session_id: str, user_id: str, correct: bool):
    field = "correct" if correct else "incorrect"

    q = f"""
    UPDATE flashcard_sessions
    SET progress_current = progress_current + 1,
        {field} = {field} + 1
    WHERE id=%s AND user_id=%s
    """
    await execute_query(q, (session_id, user_id))


async def complete_session(session_id: str, user_id: str, summary: dict):
    q = """
    UPDATE flashcard_sessions
    SET completed_at=%s,
        progress_current=%s,
        progress_total=%s,
        correct=%s,
        incorrect=%s
    WHERE id=%s AND user_id=%s
    """
    await execute_query(
        q,
        (
            utc_now_iso(),
            summary["current"],
            summary["total"],
            summary["correct"],
            summary["incorrect"],
            session_id,
            user_id,
        ),
    )
    return await get_session(session_id, user_id)
