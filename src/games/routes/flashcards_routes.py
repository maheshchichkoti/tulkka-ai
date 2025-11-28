"""
Flashcards API Routes - TULKKA Games APIs Spec
Implements: Word Lists, Words, Flashcard Sessions
"""

from fastapi import APIRouter, Depends, Request, Query, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from src.games.middlewares.auth import get_current_user
from src.games.dao.games_dao import GamesDAO
from src.games.utils import (
    ErrorCodes, raise_error, paginate, ok_response, 
    check_idempotency, store_idempotency, check_client_result_id
)
from src.db.mysql_pool import get_pool

router = APIRouter(prefix="/v1", tags=["Games - Flashcards"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class WordListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, example="Animals")
    description: Optional[str] = Field(None, example="My list of animal words")


class WordListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120, example="Animals")
    description: Optional[str] = Field(None, example="My list of animal words")
    isFavorite: Optional[bool] = None


class WordCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=120, example="Cat")
    translation: str = Field(..., min_length=1, max_length=240, example="Kissa")
    notes: Optional[str] = Field(None, example="Notes about the word")
    isFavorite: Optional[bool] = False


class WordUpdate(BaseModel):
    word: Optional[str] = Field(None, min_length=1, max_length=120, example="Cat")
    translation: Optional[str] = Field(None, min_length=1, max_length=240, example="Kissa")
    notes: Optional[str] = Field(None, example="Notes about the word")
    isFavorite: Optional[bool] = None


class FavoriteRequest(BaseModel):
    isFavorite: bool


class FlashcardSessionStart(BaseModel):
    """Start a flashcard session with one of these modes:
    - mode='custom' + wordListId: Practice user's word list
    - mode='lesson' + lessonId: Practice teacher-approved flashcards from a lesson
    - mode='topic' + topicId: Practice teacher-approved flashcards by topic
    - mode='mistakes': Practice previously incorrect words
    """
    mode: str = Field("custom", pattern="^(topic|lesson|custom|mistakes)$")
    wordListId: Optional[str] = None
    lessonId: Optional[str] = None
    topicId: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    selectedWordIds: Optional[List[str]] = None
    shuffle: Optional[bool] = False
    limit: Optional[int] = Field(None, ge=1, le=100)


class FlashcardResult(BaseModel):
    clientResultId: Optional[str] = None
    wordId: str
    isCorrect: bool
    timeSpentMs: int = Field(..., ge=0)
    attempts: int = Field(..., ge=0)


class FlashcardComplete(BaseModel):
    progress: Optional[dict] = None


# =============================================================================
# Helper Functions
# =============================================================================

async def get_pool_instance():
    """Get the MySQL connection pool."""
    return await get_pool()


def word_to_response(row: tuple) -> dict:
    """Convert a word DB row to API response format."""
    return {
        "id": row[0],
        "word": row[1],
        "translation": row[2],
        "notes": row[3],
        "isFavorite": bool(row[4]),
        "practiceCount": row[5] or 0,
        "correctCount": row[6] or 0,
        "accuracy": row[7] or 0,
        "lastPracticed": row[8].isoformat() + "Z" if row[8] else None,
        "createdAt": row[9].isoformat() + "Z" if row[9] else None,
        "updatedAt": row[10].isoformat() + "Z" if row[10] else None
    }


def _exercise_to_flashcard(row: tuple) -> dict:
    """Convert a lesson_exercises row to flashcard format.
    
    Row format: (id, exercise_data, difficulty, hint, explanation)
    exercise_data JSON contains: word, translation, example_sentence, notes, etc.
    """
    import json
    exercise_id = row[0]
    exercise_data = row[1]
    difficulty = row[2]
    hint = row[3]
    explanation = row[4]
    
    # Parse exercise_data if it's a string
    if isinstance(exercise_data, str):
        exercise_data = json.loads(exercise_data)
    
    return {
        "id": exercise_id,
        "word": exercise_data.get("word", ""),
        "translation": exercise_data.get("translation", ""),
        "notes": exercise_data.get("notes") or hint or "",
        "exampleSentence": exercise_data.get("example_sentence") or exercise_data.get("exampleSentence"),
        "difficulty": difficulty or exercise_data.get("difficulty", "medium"),
        "explanation": explanation,
        "isFavorite": False,
        "practiceCount": 0,
        "correctCount": 0,
        "accuracy": 0,
        "lastPracticed": None,
        "source": "lesson"
    }


def wordlist_to_response(row: tuple) -> dict:
    """Convert a word list DB row to API response format."""
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "wordCount": row[3] or 0,
        "isFavorite": bool(row[4]),
        "createdAt": row[5].isoformat() + "Z" if row[5] else None,
        "updatedAt": row[6].isoformat() + "Z" if row[6] else None
    }


# =============================================================================
# Word Lists Endpoints
# =============================================================================

@router.get("/word-lists")
async def list_word_lists(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    favorite: Optional[bool] = None,
    sort: Optional[str] = Query("createdAt", pattern="^(name|createdAt|updatedAt)$"),
    user=Depends(get_current_user)
):
    """GET /v1/word-lists - List user's word lists with pagination."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Build query
            where_clauses = ["user_id = %s"]
            params = [user_id]
            
            if search:
                where_clauses.append("name LIKE %s")
                params.append(f"%{search}%")
            
            if favorite is not None:
                where_clauses.append("is_favorite = %s")
                params.append(1 if favorite else 0)
            
            where_sql = " AND ".join(where_clauses)
            
            # Map sort field
            sort_map = {"name": "name", "createdAt": "created_at", "updatedAt": "updated_at"}
            sort_col = sort_map.get(sort, "created_at")
            
            # Get total count
            await cur.execute(f"SELECT COUNT(*) FROM word_lists WHERE {where_sql}", params)
            total = (await cur.fetchone())[0]
            
            # Get paginated data
            offset = (page - 1) * limit
            await cur.execute(
                f"""
                SELECT id, name, description, word_count, is_favorite, created_at, updated_at
                FROM word_lists WHERE {where_sql}
                ORDER BY {sort_col} DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset]
            )
            rows = await cur.fetchall()
    
    data = [wordlist_to_response(row) for row in rows]
    return paginate(data, page, limit, total)


@router.post(
    "/word-lists",
    status_code=201,
    summary="Create a new word list",
    responses={
        201: {
            "description": "Word list created",
            "content": {
                "application/json": {
                    "example": {
                        "id": "uuid",
                        "name": "Animals",
                        "description": "My list of animal words",
                        "wordCount": 0,
                        "isFavorite": False,
                        "createdAt": "2025-01-01T00:00:00Z",
                        "updatedAt": "2025-01-01T00:00:00Z"
                    }
                }
            }
        }
    }
)
async def create_word_list(
    payload: WordListCreate,
    user=Depends(get_current_user)
):
    """POST /v1/word-lists - Create a new word list."""
    import uuid
    pool = await get_pool_instance()
    user_id = user["userId"]
    list_id = str(uuid.uuid4())
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO word_lists (id, user_id, name, description, word_count, is_favorite)
                VALUES (%s, %s, %s, %s, 0, 0)
                """,
                (list_id, user_id, payload.name, payload.description)
            )
            await conn.commit()
            
            await cur.execute(
                "SELECT id, name, description, word_count, is_favorite, created_at, updated_at FROM word_lists WHERE id = %s",
                (list_id,)
            )
            row = await cur.fetchone()
    
    return wordlist_to_response(row)


@router.get("/word-lists/{list_id}")
async def get_word_list(
    list_id: str,
    include: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=200),
    search: Optional[str] = None,
    favorite: Optional[bool] = None,
    user=Depends(get_current_user)
):
    """GET /v1/word-lists/{listId} - Get a word list, optionally with words."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Get word list
            await cur.execute(
                """
                SELECT id, name, description, word_count, is_favorite, created_at, updated_at
                FROM word_lists WHERE id = %s AND user_id = %s
                """,
                (list_id, user_id)
            )
            row = await cur.fetchone()
            
            if not row:
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
            
            result = wordlist_to_response(row)
            
            # Include words if requested
            if include and "words" in include:
                where_clauses = ["list_id = %s"]
                params = [list_id]
                
                if search:
                    where_clauses.append("(word LIKE %s OR translation LIKE %s)")
                    params.extend([f"%{search}%", f"%{search}%"])
                
                if favorite is not None:
                    where_clauses.append("is_favorite = %s")
                    params.append(1 if favorite else 0)
                
                where_sql = " AND ".join(where_clauses)
                
                # Get total
                await cur.execute(f"SELECT COUNT(*) FROM words WHERE {where_sql}", params)
                total_words = (await cur.fetchone())[0]
                
                # Get paginated words
                offset = (page - 1) * limit
                await cur.execute(
                    f"""
                    SELECT id, word, translation, notes, is_favorite,
                           practice_count, correct_count, accuracy, last_practiced,
                           created_at, updated_at
                    FROM words WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset]
                )
                word_rows = await cur.fetchall()
                
                result["words"] = {
                    "data": [word_to_response(w) for w in word_rows],
                    "pagination": {"page": page, "limit": limit, "total": total_words}
                }
    
    return result


@router.patch("/word-lists/{list_id}")
async def update_word_list(
    list_id: str,
    payload: WordListUpdate,
    user=Depends(get_current_user)
):
    """PATCH /v1/word-lists/{listId} - Update a word list."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    # Build update fields
    updates = []
    params = []
    
    if payload.name is not None:
        updates.append("name = %s")
        params.append(payload.name)
    if payload.description is not None:
        updates.append("description = %s")
        params.append(payload.description)
    if payload.isFavorite is not None:
        updates.append("is_favorite = %s")
        params.append(1 if payload.isFavorite else 0)
    
    if not updates:
        raise_error(400, ErrorCodes.VALIDATION_ERROR, "No fields to update")
    
    params.extend([list_id, user_id])
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"UPDATE word_lists SET {', '.join(updates)} WHERE id = %s AND user_id = %s",
                params
            )
            await conn.commit()
            
            if cur.rowcount == 0:
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
            
            await cur.execute(
                "SELECT id, name, description, word_count, is_favorite, created_at, updated_at FROM word_lists WHERE id = %s",
                (list_id,)
            )
            row = await cur.fetchone()
    
    return wordlist_to_response(row)


@router.delete("/word-lists/{list_id}", status_code=204)
async def delete_word_list(
    list_id: str,
    user=Depends(get_current_user)
):
    """DELETE /v1/word-lists/{listId} - Delete a word list."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM word_lists WHERE id = %s AND user_id = %s",
                (list_id, user_id)
            )
            await conn.commit()
            
            if cur.rowcount == 0:
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
    
    return Response(status_code=204)


@router.post("/word-lists/{list_id}/favorite")
async def toggle_list_favorite(
    list_id: str,
    payload: FavoriteRequest,
    user=Depends(get_current_user)
):
    """POST /v1/word-lists/{listId}/favorite - Toggle favorite status."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE word_lists SET is_favorite = %s WHERE id = %s AND user_id = %s",
                (1 if payload.isFavorite else 0, list_id, user_id)
            )
            await conn.commit()
            
            if cur.rowcount == 0:
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
    
    return {"ok": True}


# =============================================================================
# Words Endpoints
# =============================================================================

@router.post("/word-lists/{list_id}/words", status_code=201)
async def create_word(
    list_id: str,
    payload: WordCreate,
    user=Depends(get_current_user)
):
    """POST /v1/word-lists/{listId}/words - Add a word to a list."""
    import uuid
    pool = await get_pool_instance()
    user_id = user["userId"]
    word_id = str(uuid.uuid4())
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Verify list ownership
            await cur.execute(
                "SELECT id FROM word_lists WHERE id = %s AND user_id = %s",
                (list_id, user_id)
            )
            if not await cur.fetchone():
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
            
            # Insert word
            await cur.execute(
                """
                INSERT INTO words (id, list_id, word, translation, notes, is_favorite)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (word_id, list_id, payload.word, payload.translation, payload.notes, 1 if payload.isFavorite else 0)
            )
            
            # Update word count
            await cur.execute(
                "UPDATE word_lists SET word_count = word_count + 1 WHERE id = %s",
                (list_id,)
            )
            await conn.commit()
            
            # Fetch created word
            await cur.execute(
                """
                SELECT id, word, translation, notes, is_favorite,
                       practice_count, correct_count, accuracy, last_practiced,
                       created_at, updated_at
                FROM words WHERE id = %s
                """,
                (word_id,)
            )
            row = await cur.fetchone()
    
    return word_to_response(row)


@router.patch("/word-lists/{list_id}/words/{word_id}")
async def update_word(
    list_id: str,
    word_id: str,
    payload: WordUpdate,
    user=Depends(get_current_user)
):
    """PATCH /v1/word-lists/{listId}/words/{wordId} - Update a word."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    # Build update fields
    updates = []
    params = []
    
    if payload.word is not None:
        updates.append("word = %s")
        params.append(payload.word)
    if payload.translation is not None:
        updates.append("translation = %s")
        params.append(payload.translation)
    if payload.notes is not None:
        updates.append("notes = %s")
        params.append(payload.notes)
    if payload.isFavorite is not None:
        updates.append("is_favorite = %s")
        params.append(1 if payload.isFavorite else 0)
    
    if not updates:
        raise_error(400, ErrorCodes.VALIDATION_ERROR, "No fields to update")
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Verify list ownership
            await cur.execute(
                "SELECT id FROM word_lists WHERE id = %s AND user_id = %s",
                (list_id, user_id)
            )
            if not await cur.fetchone():
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
            
            # Update word
            params.extend([word_id, list_id])
            await cur.execute(
                f"UPDATE words SET {', '.join(updates)} WHERE id = %s AND list_id = %s",
                params
            )
            await conn.commit()
            
            if cur.rowcount == 0:
                raise_error(404, ErrorCodes.UNKNOWN_WORD, "Word not found")
            
            # Fetch updated word
            await cur.execute(
                """
                SELECT id, word, translation, notes, is_favorite,
                       practice_count, correct_count, accuracy, last_practiced,
                       created_at, updated_at
                FROM words WHERE id = %s
                """,
                (word_id,)
            )
            row = await cur.fetchone()
    
    return word_to_response(row)


@router.delete("/word-lists/{list_id}/words/{word_id}", status_code=204)
async def delete_word(
    list_id: str,
    word_id: str,
    user=Depends(get_current_user)
):
    """DELETE /v1/word-lists/{listId}/words/{wordId} - Delete a word."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Verify list ownership
            await cur.execute(
                "SELECT id FROM word_lists WHERE id = %s AND user_id = %s",
                (list_id, user_id)
            )
            if not await cur.fetchone():
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
            
            # Delete word
            await cur.execute(
                "DELETE FROM words WHERE id = %s AND list_id = %s",
                (word_id, list_id)
            )
            
            if cur.rowcount == 0:
                raise_error(404, ErrorCodes.UNKNOWN_WORD, "Word not found")
            
            # Update word count
            await cur.execute(
                "UPDATE word_lists SET word_count = GREATEST(0, word_count - 1) WHERE id = %s",
                (list_id,)
            )
            await conn.commit()
    
    return Response(status_code=204)


@router.post("/word-lists/{list_id}/words/{word_id}/favorite")
async def toggle_word_favorite(
    list_id: str,
    word_id: str,
    payload: FavoriteRequest,
    user=Depends(get_current_user)
):
    """POST /v1/word-lists/{listId}/words/{wordId}/favorite - Toggle word favorite."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Verify list ownership
            await cur.execute(
                "SELECT id FROM word_lists WHERE id = %s AND user_id = %s",
                (list_id, user_id)
            )
            if not await cur.fetchone():
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
            
            await cur.execute(
                "UPDATE words SET is_favorite = %s WHERE id = %s AND list_id = %s",
                (1 if payload.isFavorite else 0, word_id, list_id)
            )
            await conn.commit()
            
            if cur.rowcount == 0:
                raise_error(404, ErrorCodes.UNKNOWN_WORD, "Word not found")
    
    return {"ok": True}


# =============================================================================
# Flashcard Catalog (Topics & Lessons for teacher-approved content)
# =============================================================================

@router.get("/flashcards/topics")
async def list_flashcard_topics(user=Depends(get_current_user)):
    """GET /v1/flashcards/topics - List available topics with flashcards."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT DISTINCT le.topic_id, le.topic_name, COUNT(*) as item_count
                FROM lesson_exercises le
                JOIN lessons l ON l.id = le.lesson_id
                WHERE le.exercise_type = 'flashcards' AND l.status = 'approved' AND le.topic_id IS NOT NULL
                GROUP BY le.topic_id, le.topic_name
                ORDER BY le.topic_name
                """
            )
            rows = await cur.fetchall()
    
    topics = [
        {"id": row[0], "name": row[1] or row[0], "itemCount": row[2]}
        for row in rows
    ]
    return {"topics": topics}


@router.get("/flashcards/lessons")
async def list_flashcard_lessons(
    topicId: Optional[str] = Query(None),
    user=Depends(get_current_user)
):
    """GET /v1/flashcards/lessons - List lessons with flashcards."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if topicId:
                await cur.execute(
                    """
                    SELECT l.id, l.title, l.lesson_date, le.topic_id, COUNT(le.id) as item_count
                    FROM lessons l
                    JOIN lesson_exercises le ON le.lesson_id = l.id
                    WHERE l.status = 'approved' AND le.exercise_type = 'flashcards' AND le.topic_id = %s
                    GROUP BY l.id, l.title, l.lesson_date, le.topic_id
                    ORDER BY l.lesson_date DESC
                    """,
                    (topicId,)
                )
            else:
                await cur.execute(
                    """
                    SELECT l.id, l.title, l.lesson_date, le.topic_id, COUNT(le.id) as item_count
                    FROM lessons l
                    JOIN lesson_exercises le ON le.lesson_id = l.id
                    WHERE l.status = 'approved' AND le.exercise_type = 'flashcards'
                    GROUP BY l.id, l.title, l.lesson_date, le.topic_id
                    ORDER BY l.lesson_date DESC
                    """
                )
            rows = await cur.fetchall()
    
    lessons = [
        {
            "id": row[0],
            "title": row[1] or f"Lesson {row[0][:8]}",
            "lessonDate": row[2].isoformat() if row[2] else None,
            "topicId": row[3],
            "itemCount": row[4]
        }
        for row in rows
    ]
    return {"lessons": lessons}


@router.get("/flashcards/mistakes")
async def list_flashcard_mistakes(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/flashcards/mistakes - List user's flashcard mistakes."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Get total count
            await cur.execute(
                "SELECT COUNT(*) FROM user_mistakes WHERE user_id = %s AND game_type = 'flashcards'",
                (user_id,)
            )
            total = (await cur.fetchone())[0]
            
            # Get paginated mistakes
            offset = (page - 1) * limit
            await cur.execute(
                """
                SELECT um.item_id, um.user_answer, um.correct_answer, um.last_answered_at,
                       w.word, w.translation
                FROM user_mistakes um
                LEFT JOIN words w ON w.id = um.item_id
                WHERE um.user_id = %s AND um.game_type = 'flashcards'
                ORDER BY um.last_answered_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset)
            )
            rows = await cur.fetchall()
    
    data = [
        {
            "itemId": row[0],
            "userAnswer": row[1],
            "correctAnswer": row[2],
            "lastAnsweredAt": row[3].isoformat() + "Z" if row[3] else None,
            "word": row[4],
            "translation": row[5]
        }
        for row in rows
    ]
    
    return paginate(data, page, limit, total)


# =============================================================================
# Flashcard Sessions
# =============================================================================

@router.post("/flashcards/sessions", status_code=201)
async def start_flashcard_session(
    payload: FlashcardSessionStart,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/flashcards/sessions - Start a new flashcard session.
    
    Modes:
    - custom: Practice user's word list (requires wordListId)
    - lesson: Practice teacher-approved flashcards from a lesson (requires lessonId)
    - topic: Practice teacher-approved flashcards by topic (requires topicId)
    - mistakes: Practice previously incorrect words
    """
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, "/v1/flashcards/sessions", idempotency_key)
        if cached:
            return JSONResponse(status_code=201, content=cached)
    
    items = []
    item_ids = []
    word_list_id = None
    lesson_id = None
    topic_id = None
    limit = payload.limit or 50
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            
            # ─────────────────────────────────────────────────────────────
            # MODE: custom - User's word list
            # ─────────────────────────────────────────────────────────────
            if payload.mode == "custom":
                if not payload.wordListId:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "wordListId required for custom mode")
                
                # Verify word list exists and belongs to user
                await cur.execute(
                    "SELECT id FROM word_lists WHERE id = %s AND user_id = %s",
                    (payload.wordListId, user_id)
                )
                if not await cur.fetchone():
                    raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
                
                word_list_id = payload.wordListId
                
                # Get words
                if payload.selectedWordIds:
                    placeholders = ",".join(["%s"] * len(payload.selectedWordIds))
                    await cur.execute(
                        f"""
                        SELECT id, word, translation, notes, is_favorite,
                               practice_count, correct_count, accuracy, last_practiced,
                               created_at, updated_at
                        FROM words WHERE id IN ({placeholders}) AND list_id = %s
                        """,
                        payload.selectedWordIds + [payload.wordListId]
                    )
                    word_rows = await cur.fetchall()
                    
                    found_ids = {row[0] for row in word_rows}
                    invalid_ids = [wid for wid in payload.selectedWordIds if wid not in found_ids]
                    if invalid_ids:
                        raise_error(400, ErrorCodes.UNKNOWN_WORD, "Unknown word IDs", {"invalidIds": invalid_ids})
                else:
                    await cur.execute(
                        """
                        SELECT id, word, translation, notes, is_favorite,
                               practice_count, correct_count, accuracy, last_practiced,
                               created_at, updated_at
                        FROM words WHERE list_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (payload.wordListId, limit)
                    )
                    word_rows = await cur.fetchall()
                
                if not word_rows:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "No words available for practice")
                
                items = [word_to_response(row) for row in word_rows]
                item_ids = [w["id"] for w in items]
            
            # ─────────────────────────────────────────────────────────────
            # MODE: lesson - Teacher-approved flashcards from a lesson
            # ─────────────────────────────────────────────────────────────
            elif payload.mode == "lesson":
                if not payload.lessonId:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "lessonId required for lesson mode")
                
                # Verify lesson exists and is approved
                await cur.execute(
                    "SELECT id, title FROM lessons WHERE id = %s AND status = 'approved'",
                    (payload.lessonId,)
                )
                lesson_row = await cur.fetchone()
                if not lesson_row:
                    raise_error(404, ErrorCodes.LESSON_NOT_FOUND, "Lesson not found or not approved")
                
                lesson_id = payload.lessonId
                
                # Get flashcard exercises from lesson
                difficulty_filter = ""
                params = [payload.lessonId]
                if payload.difficulty:
                    difficulty_filter = " AND difficulty = %s"
                    params.append(payload.difficulty)
                
                await cur.execute(
                    f"""
                    SELECT id, exercise_data, difficulty, hint, explanation
                    FROM lesson_exercises 
                    WHERE lesson_id = %s AND exercise_type = 'flashcards' {difficulty_filter}
                    LIMIT %s
                    """,
                    params + [limit]
                )
                exercise_rows = await cur.fetchall()
                
                if not exercise_rows:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "No flashcards available for this lesson")
                
                items = [_exercise_to_flashcard(row) for row in exercise_rows]
                item_ids = [item["id"] for item in items]
            
            # ─────────────────────────────────────────────────────────────
            # MODE: topic - Teacher-approved flashcards by topic
            # ─────────────────────────────────────────────────────────────
            elif payload.mode == "topic":
                if not payload.topicId:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "topicId required for topic mode")
                
                topic_id = payload.topicId
                
                # Get flashcard exercises by topic from approved lessons
                difficulty_filter = ""
                params = [payload.topicId]
                if payload.difficulty:
                    difficulty_filter = " AND le.difficulty = %s"
                    params.append(payload.difficulty)
                
                await cur.execute(
                    f"""
                    SELECT le.id, le.exercise_data, le.difficulty, le.hint, le.explanation
                    FROM lesson_exercises le
                    JOIN lessons l ON l.id = le.lesson_id
                    WHERE le.topic_id = %s AND le.exercise_type = 'flashcards' AND l.status = 'approved' {difficulty_filter}
                    LIMIT %s
                    """,
                    params + [limit]
                )
                exercise_rows = await cur.fetchall()
                
                if not exercise_rows:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "No flashcards available for this topic")
                
                items = [_exercise_to_flashcard(row) for row in exercise_rows]
                item_ids = [item["id"] for item in items]
            
            # ─────────────────────────────────────────────────────────────
            # MODE: mistakes - Practice previously incorrect words
            # ─────────────────────────────────────────────────────────────
            elif payload.mode == "mistakes":
                # Get user's mistakes for flashcards
                await cur.execute(
                    """
                    SELECT item_id FROM user_mistakes 
                    WHERE user_id = %s AND game_type = 'flashcards'
                    ORDER BY last_answered_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit)
                )
                mistake_rows = await cur.fetchall()
                
                if not mistake_rows:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "No mistakes to practice")
                
                mistake_ids = [row[0] for row in mistake_rows]
                
                # Try to fetch from words table first (user-created)
                placeholders = ",".join(["%s"] * len(mistake_ids))
                await cur.execute(
                    f"""
                    SELECT id, word, translation, notes, is_favorite,
                           practice_count, correct_count, accuracy, last_practiced,
                           created_at, updated_at
                    FROM words WHERE id IN ({placeholders})
                    """,
                    mistake_ids
                )
                word_rows = await cur.fetchall()
                
                if word_rows:
                    items = [word_to_response(row) for row in word_rows]
                    item_ids = [w["id"] for w in items]
                else:
                    # Try lesson_exercises
                    await cur.execute(
                        f"""
                        SELECT id, exercise_data, difficulty, hint, explanation
                        FROM lesson_exercises WHERE id IN ({placeholders})
                        """,
                        mistake_ids
                    )
                    exercise_rows = await cur.fetchall()
                    if exercise_rows:
                        items = [_exercise_to_flashcard(row) for row in exercise_rows]
                        item_ids = [item["id"] for item in items]
                    else:
                        raise_error(400, ErrorCodes.VALIDATION_ERROR, "No mistakes to practice")
            
            else:
                raise_error(400, ErrorCodes.VALIDATION_ERROR, f"Invalid mode: {payload.mode}")
    
    # Create session using GamesDAO
    session = await dao.create_session(
        user_id=user_id,
        game_type="flashcards",
        item_ids=item_ids,
        shuffle=payload.shuffle or False,
        word_list_id=word_list_id,
        lesson_id=lesson_id,
        topic_id=topic_id,
        mode=payload.mode
    )
    
    # Reorder items to match session order
    item_map = {item["id"]: item for item in items}
    ordered_items = [item_map[iid] for iid in session["itemOrder"] if iid in item_map]
    
    response = {
        "id": session["id"],
        "mode": payload.mode,
        "wordListId": word_list_id,
        "lessonId": lesson_id,
        "topicId": topic_id,
        "words": ordered_items,  # Use "words" for backward compatibility
        "progress": session["progress"],
        "startedAt": session["startedAt"],
        "completedAt": None
    }
    
    # Store idempotency
    if idempotency_key:
        await store_idempotency(pool, user_id, "/v1/flashcards/sessions", idempotency_key, response)
    
    return JSONResponse(
        status_code=201,
        content=response,
        headers={"Location": f"/v1/flashcards/sessions/{session['id']}"}
    )


@router.get("/flashcards/sessions/{session_id}")
async def get_flashcard_session(
    session_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/flashcards/sessions/{sessionId} - Get session state for resume."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["gameType"] != "flashcards":
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    # Fetch words in session order
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if session["itemOrder"]:
                placeholders = ",".join(["%s"] * len(session["itemOrder"]))
                await cur.execute(
                    f"""
                    SELECT id, word, translation, notes, is_favorite,
                           practice_count, correct_count, accuracy, last_practiced,
                           created_at, updated_at
                    FROM words WHERE id IN ({placeholders})
                    """,
                    session["itemOrder"]
                )
                word_rows = await cur.fetchall()
                word_map = {row[0]: word_to_response(row) for row in word_rows}
                words = [word_map[wid] for wid in session["itemOrder"] if wid in word_map]
            else:
                words = []
    
    return {
        "id": session["id"],
        "wordListId": session["wordListId"],
        "words": words,
        "progress": session["progress"],
        "startedAt": session["startedAt"],
        "completedAt": session["completedAt"]
    }


@router.post("/flashcards/sessions/{session_id}/results")
async def record_flashcard_result(
    session_id: str,
    payload: FlashcardResult,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/flashcards/sessions/{sessionId}/results - Record a practice result."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    endpoint = f"/v1/flashcards/sessions/{session_id}/results"
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, endpoint, idempotency_key)
        if cached:
            return cached
    
    # Check clientResultId deduplication
    if payload.clientResultId:
        existing = await check_client_result_id(pool, session_id, payload.clientResultId)
        if existing:
            # Return the existing result
            session = await dao.get_session(session_id)
            return {"ok": True, "progress": session["progress"], "word": existing}
    
    # Get session
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["status"] == "completed":
        raise_error(409, ErrorCodes.SESSION_COMPLETED, "Session already completed")
    
    # Validate word ID is in session
    if payload.wordId not in session["itemOrder"]:
        raise_error(400, ErrorCodes.UNKNOWN_WORD, "Word not in session", {"invalidIds": [payload.wordId]})
    
    # Insert result
    await dao.insert_result(
        session_id=session_id,
        item_id=payload.wordId,
        is_correct=payload.isCorrect,
        attempts=payload.attempts,
        time_spent_ms=payload.timeSpentMs,
        client_result_id=payload.clientResultId
    )
    
    # Update session progress
    progress = await dao.update_session_progress(session_id, payload.isCorrect, payload.wordId)
    
    # Update word statistics
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE words SET
                    practice_count = practice_count + 1,
                    correct_count = correct_count + %s,
                    accuracy = ROUND(100 * (correct_count + %s) / (practice_count + 1)),
                    last_practiced = NOW()
                WHERE id = %s
                """,
                (1 if payload.isCorrect else 0, 1 if payload.isCorrect else 0, payload.wordId)
            )
            await conn.commit()
            
            # Fetch updated word
            await cur.execute(
                """
                SELECT id, word, translation, notes, is_favorite,
                       practice_count, correct_count, accuracy, last_practiced,
                       created_at, updated_at
                FROM words WHERE id = %s
                """,
                (payload.wordId,)
            )
            word_row = await cur.fetchone()
    
    # Track mistake if incorrect
    if not payload.isCorrect:
        await dao.record_mistake(user_id, "flashcards", payload.wordId)
    else:
        await dao.remove_mistake(user_id, "flashcards", payload.wordId)
    
    word_partial = {
        "id": word_row[0],
        "practiceCount": word_row[5],
        "correctCount": word_row[6],
        "accuracy": word_row[7],
        "lastPracticed": word_row[8].isoformat() + "Z" if word_row[8] else None
    }
    
    response = {"ok": True, "progress": progress, "word": word_partial}
    
    # Store idempotency
    if idempotency_key:
        await store_idempotency(pool, user_id, endpoint, idempotency_key, response)
    
    return response


@router.post("/flashcards/sessions/{session_id}/complete")
async def complete_flashcard_session(
    session_id: str,
    payload: FlashcardComplete = None,
    user=Depends(get_current_user)
):
    """POST /v1/flashcards/sessions/{sessionId}/complete - Complete a session."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Get session
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["status"] == "completed":
        raise_error(409, ErrorCodes.SESSION_COMPLETED, "Session already completed")
    
    # Complete session
    completed_session = await dao.complete_session(session_id)
    
    return {
        "id": completed_session["id"],
        "wordListId": completed_session["wordListId"],
        "words": [],  # Empty per spec
        "progress": completed_session["progress"],
        "masteredWordIds": completed_session["masteredIds"],
        "needsPracticeWordIds": completed_session["needsPracticeIds"],
        "startedAt": completed_session["startedAt"],
        "completedAt": completed_session["completedAt"]
    }


# =============================================================================
# Stats Endpoint
# =============================================================================

@router.get("/flashcards/stats/me")
async def get_flashcard_stats(user=Depends(get_current_user)):
    """GET /v1/flashcards/stats/me - Get user's flashcard statistics."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 
                    COUNT(*) as totalSessions,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completedSessions,
                    SUM(correct_count) as totalCorrect,
                    SUM(incorrect_count) as totalIncorrect
                FROM game_sessions
                WHERE user_id = %s AND game_type = 'flashcards'
                """,
                (user_id,)
            )
            row = await cur.fetchone()
    
    return {
        "totalSessions": row[0] or 0,
        "completedSessions": row[1] or 0,
        "totalCorrect": row[2] or 0,
        "totalIncorrect": row[3] or 0,
        "accuracy": round(100 * (row[2] or 0) / max(1, (row[2] or 0) + (row[3] or 0)))
    }
