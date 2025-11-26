from typing import Optional, List, Dict, Any
from src.db.mysql_pool import execute_query

class FlashcardsDAO:

    async def fetch_list_words(self, list_id: str) -> List[Dict[str, Any]]:
        q = """
        SELECT * FROM words
        WHERE list_id = %s
        ORDER BY created_at ASC
        """
        return await execute_query(q, (list_id,), fetchall=True)

    async def fetch_subset_words(self, list_id: str, ids: List[str]):
        if not ids:
            return []
        placeholders = ",".join(["%s"] * len(ids))
        q = f"""
        SELECT * FROM words
        WHERE list_id = %s AND id IN ({placeholders})
        ORDER BY created_at ASC
        """
        return await execute_query(q, (list_id, *ids), fetchall=True)

    async def create_session(self, session_id: str, user_id: str, list_id: str, total: int):
        q = """
        INSERT INTO flashcard_sessions
        (id, user_id, list_id, started_at, progress_current, progress_total, correct, incorrect)
        VALUES (%s, %s, %s, UTC_TIMESTAMP(), 0, %s, 0, 0)
        """
        await execute_query(q, (session_id, user_id, list_id, total))

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        q = "SELECT * FROM flashcard_sessions WHERE id = %s"
        return await execute_query(q, (session_id,), fetchone=True)

    async def insert_result(self, session_id: str, word_id: str, is_correct: bool, attempts: int, time_ms: int):
        q = """
        INSERT INTO flashcard_results (session_id, word_id, is_correct, attempts, time_spent_ms, created_at)
        VALUES (%s, %s, %s, %s, %s, UTC_TIMESTAMP())
        """
        await execute_query(q, (session_id, word_id, int(is_correct), attempts, time_ms))

    async def update_word_stats(self, word_id: str, is_correct: bool):
        # First update counts
        q = """
        UPDATE words
        SET practice_count = practice_count + 1,
            correct_count = correct_count + %s,
            last_practiced = UTC_TIMESTAMP()
        WHERE id = %s
        """
        await execute_query(q, (1 if is_correct else 0, word_id))

        # Then update accuracy based on new counts
        q2 = """
        UPDATE words
        SET accuracy = ROUND(100.0 * correct_count / GREATEST(practice_count, 1))
        WHERE id = %s
        """
        await execute_query(q2, (word_id,))

    async def update_session_progress(self, session_id: str, is_correct: bool):
        q = """
        UPDATE flashcard_sessions
        SET progress_current = progress_current + 1,
            correct = correct + %s,
            incorrect = incorrect + %s
        WHERE id = %s
        """
        await execute_query(q, (1 if is_correct else 0, 0 if is_correct else 1, session_id))

    async def complete_session(self, session_id: str, progress: dict | None):
        if progress:
            q = """
            UPDATE flashcard_sessions
            SET completed_at = UTC_TIMESTAMP(),
                status = 'completed',
                progress_current = %s,
                progress_total = %s,
                correct = %s,
                incorrect = %s
            WHERE id = %s
            """
            await execute_query(
                q,
                (
                    progress["current"],
                    progress["total"],
                    progress["correct"],
                    progress["incorrect"],
                    session_id,
                ),
            )
        else:
            q = "UPDATE flashcard_sessions SET completed_at = UTC_TIMESTAMP(), status = 'completed' WHERE id = %s"
            await execute_query(q, (session_id,))
