"""
Unified Games DAO for TULKKA Games APIs.
Handles game_sessions, game_results and user_mistakes tables for all game types.
"""

import json
import uuid
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Note: 'pool' is expected to be an aiomysql pool or similar async DB pool
class GamesDAO:
    """Data Access Object for unified game sessions and results."""

    # Game types considered removable mistakes
    REMOVABLE_MISTAKE_TYPES = {"flashcards", "spelling_bee"}

    def __init__(self, pool):
        self.pool = pool

    # =========================================================================
    # Session Operations
    # =========================================================================

    async def create_session(
        self,
        user_id: str,
        game_type: str,
        item_ids: List[str],
        shuffle: bool = False,
        word_list_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        category_id: Optional[str] = None,
        lesson_id: Optional[str] = None,
        class_id: Optional[str] = None,
        mode: str = "topic",
        difficulty: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new game session and persist it.

        Returns a session dict (not necessarily mirroring DB timestamps exactly).
        """
        session_id = str(uuid.uuid4())

        # Ensure deterministic copy and optionally shuffle
        ordered_ids = list(item_ids or [])
        if shuffle:
            random.shuffle(ordered_ids)

        progress_total = len(ordered_ids)

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO game_sessions (
                        id, user_id, game_type, mode,
                        word_list_id, topic_id, category_id, lesson_id, class_id,
                        difficulty, item_order,
                        progress_current, progress_total, correct_count, incorrect_count,
                        mastered_ids, needs_practice_ids, status
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s,
                        0, %s, 0, 0,
                        %s, %s, 'active'
                    )
                    """,
                    (
                        session_id, user_id, game_type, mode,
                        word_list_id, topic_id, category_id, lesson_id, class_id,
                        difficulty, json.dumps(ordered_ids),
                        progress_total,
                        json.dumps([]), json.dumps([])
                    )
                )
                await conn.commit()

        return {
            "id": session_id,
            "userId": user_id,
            "gameType": game_type,
            "mode": mode,
            "wordListId": word_list_id,
            "topicId": topic_id,
            "categoryId": category_id,
            "lessonId": lesson_id,
            "classId": class_id,
            "difficulty": difficulty,
            "itemOrder": ordered_ids,
            "progress": {
                "current": 0,
                "total": progress_total,
                "correct": 0,
                "incorrect": 0
            },
            "masteredIds": [],
            "needsPracticeIds": [],
            "startedAt": datetime.utcnow().isoformat() + "Z",
            "completedAt": None,
            "status": "active"
        }

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID. Returns None if not found."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        id, user_id, game_type, mode,
                        word_list_id, topic_id, category_id, lesson_id, class_id,
                        difficulty, item_order,
                        progress_current, progress_total, correct_count, incorrect_count,
                        mastered_ids, needs_practice_ids,
                        started_at, completed_at, status
                    FROM game_sessions WHERE id = %s
                    """,
                    (session_id,)
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return self._row_to_session(row)

    async def update_session_progress(
        self,
        session_id: str,
        is_correct: bool,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Update session progress after a result and return the new progress object.

        Returns progress dict or None if session not found.
        """
        async with self.pool.acquire() as conn:
            try:
                async with conn.cursor() as cur:
                    # Lock the session row to avoid race conditions
                    await cur.execute(
                        """
                        SELECT 
                            progress_current, progress_total, correct_count, incorrect_count,
                            mastered_ids, needs_practice_ids
                        FROM game_sessions WHERE id = %s FOR UPDATE
                        """,
                        (session_id,)
                    )
                    row = await cur.fetchone()
                    if not row:
                        # Nothing to update; ensure transaction is clean
                        await conn.rollback()
                        return None

                    current, total, correct, incorrect, mastered_json, needs_json = row

                    # Parse JSON arrays safely
                    mastered = json.loads(mastered_json) if mastered_json else []
                    needs_practice = json.loads(needs_json) if needs_json else []

                    # Update counters
                    new_current = min(current + 1, total)
                    new_correct = correct + (1 if is_correct else 0)
                    new_incorrect = incorrect + (0 if is_correct else 1)

                    # Update mastery lists deterministically
                    if is_correct:
                        if item_id not in mastered:
                            mastered.append(item_id)
                        if item_id in needs_practice:
                            needs_practice.remove(item_id)
                    else:
                        if item_id in mastered:
                            mastered.remove(item_id)
                        if item_id not in needs_practice:
                            needs_practice.append(item_id)

                    # Persist changes
                    await cur.execute(
                        """
                        UPDATE game_sessions SET
                            progress_current = %s,
                            correct_count = %s,
                            incorrect_count = %s,
                            mastered_ids = %s,
                            needs_practice_ids = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (
                            new_current, new_correct, new_incorrect,
                            json.dumps(mastered), json.dumps(needs_practice),
                            session_id
                        )
                    )
                    await conn.commit()

                    return {
                        "current": new_current,
                        "total": total,
                        "correct": new_correct,
                        "incorrect": new_incorrect
                    }
            except Exception:
                try:
                    await conn.rollback()
                except Exception:
                    # If rollback itself fails, we still re-raise the original error
                    pass
                raise

    async def complete_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Mark a session as completed and return final state; returns None if not updated."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE game_sessions SET
                        status = 'completed',
                        completed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s AND status = 'active'
                    """,
                    (session_id,)
                )
                await conn.commit()
                if cur.rowcount == 0:
                    return None
        return await self.get_session(session_id)

    # =========================================================================
    # Result Operations
    # =========================================================================

    async def insert_result(
        self,
        session_id: str,
        item_id: str,
        is_correct: bool,
        attempts: int = 1,
        time_spent_ms: int = 0,
        skipped: bool = False,
        user_answer: Optional[str] = None,
        selected_answer: Optional[int] = None,
        selected_answers: Optional[List[str]] = None,
        user_tokens: Optional[List[str]] = None,
        error_type: Optional[str] = None,
        client_result_id: Optional[str] = None
    ) -> int:
        """Insert a game result and return the inserted row id."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO game_results (
                        session_id, item_id, client_result_id,
                        is_correct, attempts, time_spent_ms, skipped,
                        user_answer, selected_answer, selected_answers,
                        user_tokens, error_type
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s
                    )
                    """,
                    (
                        session_id, item_id, client_result_id,
                        1 if is_correct else 0, attempts, time_spent_ms, 1 if skipped else 0,
                        user_answer, selected_answer,
                        json.dumps(selected_answers) if selected_answers is not None else None,
                        json.dumps(user_tokens) if user_tokens is not None else None,
                        error_type
                    )
                )
                await conn.commit()
                return cur.lastrowid

    async def get_session_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all results for a session ordered by creation time."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 
                        id, item_id, client_result_id,
                        is_correct, attempts, time_spent_ms, skipped,
                        user_answer, selected_answer, selected_answers,
                        user_tokens, error_type, created_at
                    FROM game_results WHERE session_id = %s
                    ORDER BY created_at ASC
                    """,
                    (session_id,)
                )
                rows = await cur.fetchall()
                return [self._row_to_result(row) for row in rows]

    # =========================================================================
    # Mistake Operations
    # =========================================================================

    async def record_mistake(
        self,
        user_id: str,
        game_type: str,
        item_id: str,
        user_answer: Optional[str] = None,
        correct_answer: Optional[str] = None,
        selected_answers: Optional[List[str]] = None,
        error_type: Optional[str] = None
    ) -> None:
        """Record or update a user mistake.

        For both removable and permanent mistake types we upsert and increment mistake_count.
        Permanence is handled by remove_mistake (it will be a no-op for permanent types).
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO user_mistakes (
                        user_id, game_type, item_id,
                        user_answer, correct_answer, selected_answers, error_type,
                        mistake_count, last_answered_at
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        1, NOW()
                    )
                    ON DUPLICATE KEY UPDATE
                        user_answer = VALUES(user_answer),
                        correct_answer = VALUES(correct_answer),
                        selected_answers = VALUES(selected_answers),
                        error_type = VALUES(error_type),
                        mistake_count = mistake_count + 1,
                        last_answered_at = NOW(),
                        updated_at = NOW()
                    """,
                    (
                        user_id, game_type, item_id,
                        user_answer, correct_answer,
                        json.dumps(selected_answers) if selected_answers is not None else None,
                        error_type
                    )
                )
                await conn.commit()

    async def remove_mistake(
        self,
        user_id: str,
        game_type: str,
        item_id: str
    ) -> None:
        """Remove or decrement a user mistake.

        - For REMOVABLE_MISTAKE_TYPES (flashcards, spelling_bee): decrement mistake_count and delete row when <= 0.
        - For permanent types (grammar_challenge, advanced_cloze, sentence_builder): DO NOTHING.
        """
        if game_type not in self.REMOVABLE_MISTAKE_TYPES:
            # Permanent mistakes — do not decrement or delete
            return

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Decrement
                await cur.execute(
                    """
                    UPDATE user_mistakes
                    SET mistake_count = GREATEST(mistake_count - 1, 0),
                        updated_at = NOW()
                    WHERE user_id = %s AND game_type = %s AND item_id = %s
                    """,
                    (user_id, game_type, item_id)
                )
                # Remove rows where count <= 0
                await cur.execute(
                    """
                    DELETE FROM user_mistakes
                    WHERE user_id = %s AND game_type = %s AND item_id = %s AND mistake_count <= 0
                    """,
                    (user_id, game_type, item_id)
                )
                await conn.commit()

    async def get_user_mistakes(
        self,
        user_id: str,
        game_type: str,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated user mistakes for a game type."""
        offset = (page - 1) * limit

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*) FROM user_mistakes
                    WHERE user_id = %s AND game_type = %s
                    """,
                    (user_id, game_type)
                )
                total_row = await cur.fetchone()
                total = total_row[0] if total_row else 0

                await cur.execute(
                    """
                    SELECT 
                        item_id, user_answer, correct_answer,
                        selected_answers, error_type,
                        mistake_count, last_answered_at
                    FROM user_mistakes
                    WHERE user_id = %s AND game_type = %s
                    ORDER BY last_answered_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, game_type, limit, offset)
                )
                rows = await cur.fetchall()

                mistakes = []
                for row in rows:
                    mistakes.append({
                        "itemId": row[0],
                        "userAnswer": row[1],
                        "correctAnswer": row[2],
                        "selectedAnswers": json.loads(row[3]) if row[3] else None,
                        "errorType": row[4],
                        "mistakeCount": row[5],
                        "lastAnsweredAt": row[6].isoformat() + "Z" if row[6] else None
                    })

                return mistakes, total

    async def get_mistake_item_ids(
        self,
        user_id: str,
        game_type: str,
        limit: int = 50
    ) -> List[str]:
        """Get item IDs appropriate for mistakes-mode sessions (ordered by severity/recentness)."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT item_id FROM user_mistakes
                    WHERE user_id = %s AND game_type = %s
                    ORDER BY mistake_count DESC, last_answered_at DESC
                    LIMIT %s
                    """,
                    (user_id, game_type, limit)
                )
                rows = await cur.fetchall()
                return [r[0] for r in rows] if rows else []

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_session(self, row: tuple) -> Dict[str, Any]:
        """Convert a database row to a session dict."""
        # handle nulls and JSON safely
        item_order = []
        try:
            item_order = json.loads(row[10]) if row[10] else []
        except Exception:
            item_order = []

        mastered = []
        needs = []
        try:
            mastered = json.loads(row[15]) if row[15] else []
        except Exception:
            mastered = []
        try:
            needs = json.loads(row[16]) if row[16] else []
        except Exception:
            needs = []

        return {
            "id": row[0],
            "userId": row[1],
            "gameType": row[2],
            "mode": row[3],
            "wordListId": row[4],
            "topicId": row[5],
            "categoryId": row[6],
            "lessonId": row[7],
            "classId": row[8],
            "difficulty": row[9],
            "itemOrder": item_order,
            "progress": {
                "current": row[11],
                "total": row[12],
                "correct": row[13],
                "incorrect": row[14]
            },
            "masteredIds": mastered,
            "needsPracticeIds": needs,
            "startedAt": row[17].isoformat() + "Z" if row[17] else None,
            "completedAt": row[18].isoformat() + "Z" if row[18] else None,
            "status": row[19]
        }

    def _row_to_result(self, row: tuple) -> Dict[str, Any]:
        """Convert a database row to a result dict."""
        selected_answers = None
        user_tokens = None
        try:
            selected_answers = json.loads(row[9]) if row[9] else None
        except Exception:
            selected_answers = None
        try:
            user_tokens = json.loads(row[10]) if row[10] else None
        except Exception:
            user_tokens = None

        return {
            "id": row[0],
            "itemId": row[1],
            "clientResultId": row[2],
            "isCorrect": bool(row[3]),
            "attempts": row[4],
            "timeSpentMs": row[5],
            "skipped": bool(row[6]),
            "userAnswer": row[7],
            "selectedAnswer": row[8],
            "selectedAnswers": selected_answers,
            "userTokens": user_tokens,
            "errorType": row[11],
            "createdAt": row[12].isoformat() + "Z" if row[12] else None
        }
