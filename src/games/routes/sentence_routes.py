"""
Sentence Builder API Routes - TULKKA Games APIs Spec
Implements: Topics, Lessons, Items, Sessions, Hints, TTS, Mistakes
"""

import json
from fastapi import APIRouter, Depends, Request, Query, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

from src.games.middlewares.auth import get_current_user
from src.games.dao.games_dao import GamesDAO
from src.games.utils import (
    ErrorCodes, raise_error, paginate, ok_response,
    check_idempotency, store_idempotency, check_client_result_id
)
from src.db.mysql_pool import get_pool

router = APIRouter(prefix="/v1/sentence-builder", tags=["Games - Sentence Builder"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class SentenceSessionStart(BaseModel):
    mode: Literal["topic", "lesson", "custom", "mistakes"]
    topicId: Optional[str] = None
    lessonId: Optional[str] = None
    selectedItemIds: Optional[List[str]] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    limit: Optional[int] = Field(None, ge=1, le=50)
    shuffle: Optional[bool] = True


class SentenceResult(BaseModel):
    clientResultId: Optional[str] = None
    itemId: str
    userTokens: List[str]
    isCorrect: bool
    attempts: int = Field(..., ge=0)
    timeSpentMs: int = Field(..., ge=0)
    errorType: Optional[str] = None  # word_order, missing_words, extra_words


class SentenceComplete(BaseModel):
    progress: Optional[dict] = None


# =============================================================================
# Helper Functions
# =============================================================================

async def get_pool_instance():
    """Get the MySQL connection pool."""
    return await get_pool()


def item_to_response(row: tuple, include_answer: bool = False) -> dict:
    """Convert a lesson_exercises row to Sentence Item format."""
    exercise_data = row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {}
    
    response = {
        "id": row[0],
        "english": exercise_data.get("english", ""),
        "translation": exercise_data.get("translation", ""),
        "tokens": exercise_data.get("tokens", []),
        "distractors": exercise_data.get("distractors", []),
        "topic": row[3] or exercise_data.get("topic"),
        "difficulty": row[4] or exercise_data.get("difficulty", "medium"),
    }
    
    if include_answer:
        response["accepted"] = exercise_data.get("accepted", [])
    
    return response


def check_sentence_answer(user_tokens: List[str], accepted: List[List[str]]) -> tuple[bool, Optional[str]]:
    """
    Check if user's token order matches any accepted answer.
    Returns (is_correct, error_type).
    """
    user_sentence = user_tokens
    
    for accepted_tokens in accepted:
        if user_sentence == accepted_tokens:
            return True, None
    
    # Determine error type
    if not accepted:
        return False, "word_order"
    
    first_accepted = accepted[0]
    user_set = set(user_tokens)
    accepted_set = set(first_accepted)
    
    if user_set == accepted_set:
        return False, "word_order"
    elif len(user_tokens) < len(first_accepted):
        return False, "missing_words"
    elif len(user_tokens) > len(first_accepted):
        return False, "extra_words"
    else:
        return False, "word_order"


# =============================================================================
# Catalog Endpoints
# =============================================================================

@router.get("/topics")
async def get_sentence_topics(
    user=Depends(get_current_user)
):
    """GET /v1/sentence-builder/topics - Get available sentence topics."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT DISTINCT le.topic_id, le.topic_name, COUNT(*) as itemCount
                FROM lesson_exercises le
                JOIN lessons l ON l.id = le.lesson_id
                WHERE le.exercise_type = 'sentence_builder' AND l.status = 'approved'
                GROUP BY le.topic_id, le.topic_name
                ORDER BY le.topic_name
                """
            )
            rows = await cur.fetchall()
    
    topics = []
    for row in rows:
        topics.append({
            "id": row[0] or "general",
            "name": row[1] or "General Sentences",
            "itemCount": row[2]
        })
    
    return {"data": topics}


@router.get("/lessons")
async def get_sentence_lessons(
    topicId: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/sentence-builder/lessons - Get sentence lessons."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            where_clauses = ["le.exercise_type = 'sentence_builder'", "l.status = 'approved'"]
            params = []
            
            if topicId:
                where_clauses.append("le.topic_id = %s")
                params.append(topicId)
            
            where_sql = " AND ".join(where_clauses)
            
            # Get total
            await cur.execute(
                f"""
                SELECT COUNT(DISTINCT l.id)
                FROM lessons l
                JOIN lesson_exercises le ON le.lesson_id = l.id
                WHERE {where_sql}
                """,
                params
            )
            total = (await cur.fetchone())[0]
            
            # Get paginated lessons
            offset = (page - 1) * limit
            await cur.execute(
                f"""
                SELECT l.id, l.title, l.lesson_number, l.class_id, l.created_at,
                       COUNT(le.id) as itemCount
                FROM lessons l
                JOIN lesson_exercises le ON le.lesson_id = l.id
                WHERE {where_sql}
                GROUP BY l.id
                ORDER BY l.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset]
            )
            rows = await cur.fetchall()
    
    lessons = []
    for row in rows:
        lessons.append({
            "id": row[0],
            "title": row[1] or f"Lesson {row[2]}",
            "lessonNumber": row[2],
            "classId": row[3],
            "itemCount": row[5],
            "createdAt": row[4].isoformat() + "Z" if row[4] else None
        })
    
    return paginate(lessons, page, limit, total)


@router.get("/items")
async def get_sentence_items(
    topicId: Optional[str] = None,
    lessonId: Optional[str] = None,
    difficulty: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/sentence-builder/items - Get sentence items catalog."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            where_clauses = ["le.exercise_type = 'sentence_builder'", "l.status = 'approved'"]
            params = []
            
            if topicId:
                where_clauses.append("le.topic_id = %s")
                params.append(topicId)
            
            if lessonId:
                where_clauses.append("le.lesson_id = %s")
                params.append(lessonId)
            
            if difficulty:
                where_clauses.append("le.difficulty = %s")
                params.append(difficulty)
            
            where_sql = " AND ".join(where_clauses)
            
            # Get total
            await cur.execute(
                f"""
                SELECT COUNT(*) FROM lesson_exercises le
                JOIN lessons l ON l.id = le.lesson_id
                WHERE {where_sql}
                """,
                params
            )
            total = (await cur.fetchone())[0]
            
            # Get paginated items
            offset = (page - 1) * limit
            await cur.execute(
                f"""
                SELECT le.id, le.lesson_id, le.exercise_data, le.topic_id, le.difficulty, le.hint
                FROM lesson_exercises le
                JOIN lessons l ON l.id = le.lesson_id
                WHERE {where_sql}
                ORDER BY le.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset]
            )
            rows = await cur.fetchall()
    
    items = [item_to_response(row, include_answer=False) for row in rows]
    return paginate(items, page, limit, total)


# =============================================================================
# Session Endpoints
# =============================================================================

@router.post("/sessions", status_code=201)
async def start_sentence_session(
    payload: SentenceSessionStart,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/sentence-builder/sessions - Start a new sentence session."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, "/v1/sentence-builder/sessions", idempotency_key)
        if cached:
            return JSONResponse(status_code=201, content=cached)
    
    items = []
    item_ids = []
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if payload.mode == "custom" and payload.selectedItemIds:
                placeholders = ",".join(["%s"] * len(payload.selectedItemIds))
                await cur.execute(
                    f"""
                    SELECT le.id, le.lesson_id, le.exercise_data, le.topic_id, le.difficulty, le.hint
                    FROM lesson_exercises le
                    JOIN lessons l ON l.id = le.lesson_id
                    WHERE le.id IN ({placeholders}) AND le.exercise_type = 'sentence_builder' AND l.status = 'approved'
                    """,
                    payload.selectedItemIds
                )
                rows = await cur.fetchall()
                
                found_ids = {row[0] for row in rows}
                invalid_ids = [iid for iid in payload.selectedItemIds if iid not in found_ids]
                if invalid_ids:
                    raise_error(400, ErrorCodes.UNKNOWN_ITEM, "Unknown item IDs", {"invalidIds": invalid_ids})
                
            elif payload.mode == "mistakes":
                mistake_ids = await dao.get_mistake_item_ids(user_id, "sentence_builder", payload.limit or 20)
                if not mistake_ids:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "No mistakes to review")
                
                placeholders = ",".join(["%s"] * len(mistake_ids))
                await cur.execute(
                    f"""
                    SELECT le.id, le.lesson_id, le.exercise_data, le.topic_id, le.difficulty, le.hint
                    FROM lesson_exercises le
                    JOIN lessons l ON l.id = le.lesson_id
                    WHERE le.id IN ({placeholders}) AND le.exercise_type = 'sentence_builder' AND l.status = 'approved'
                    """,
                    mistake_ids
                )
                rows = await cur.fetchall()
                
            elif payload.mode == "lesson" and payload.lessonId:
                await cur.execute(
                    """
                    SELECT le.id, le.lesson_id, le.exercise_data, le.topic_id, le.difficulty, le.hint
                    FROM lesson_exercises le
                    JOIN lessons l ON l.id = le.lesson_id
                    WHERE le.lesson_id = %s AND le.exercise_type = 'sentence_builder' AND l.status = 'approved'
                    ORDER BY le.created_at
                    LIMIT %s
                    """,
                    (payload.lessonId, 8)
                )
                rows = await cur.fetchall()
                
            else:
                # Topic mode (default)
                where_clauses = ["le.exercise_type = 'sentence_builder'", "l.status = 'approved'"]
                params = []
                
                if payload.topicId:
                    where_clauses.append("le.topic_id = %s")
                    params.append(payload.topicId)
                
                if payload.difficulty:
                    where_clauses.append("le.difficulty = %s")
                    params.append(payload.difficulty)
                
                where_sql = " AND ".join(where_clauses)
                params.append(8)  # Fixed limit of 8 items per session
                
                await cur.execute(
                    f"""
                    SELECT le.id, le.lesson_id, le.exercise_data, le.topic_id, le.difficulty, le.hint
                    FROM lesson_exercises le
                    JOIN lessons l ON l.id = le.lesson_id
                    WHERE {where_sql}
                    ORDER BY RAND()
                    LIMIT %s
                    """,
                    params
                )
                rows = await cur.fetchall()
            
            if not rows:
                raise_error(400, ErrorCodes.VALIDATION_ERROR, "No items available")
            
            items = [item_to_response(row, include_answer=True) for row in rows]
            item_ids = [i["id"] for i in items]
    
    # Create session
    session = await dao.create_session(
        user_id=user_id,
        game_type="sentence_builder",
        item_ids=item_ids,
        shuffle=payload.shuffle if payload.shuffle is not None else True,
        topic_id=payload.topicId,
        lesson_id=payload.lessonId,
        mode=payload.mode,
        difficulty=payload.difficulty
    )
    
    # Reorder items to match session order
    item_map = {i["id"]: i for i in items}
    ordered_items = [item_map[iid] for iid in session["itemOrder"] if iid in item_map]
    
    response = {
        "id": session["id"],
        "mode": payload.mode,
        "topicId": payload.topicId,
        "lessonId": payload.lessonId,
        "difficulty": payload.difficulty,
        "items": ordered_items,
        "progress": session["progress"],
        "startedAt": session["startedAt"],
        "completedAt": None
    }
    
    if idempotency_key:
        await store_idempotency(pool, user_id, "/v1/sentence-builder/sessions", idempotency_key, response)
    
    return JSONResponse(
        status_code=201,
        content=response,
        headers={"Location": f"/v1/sentence-builder/sessions/{session['id']}"}
    )


@router.get("/sessions/{session_id}")
async def get_sentence_session(
    session_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/sentence-builder/sessions/{sessionId} - Get session state for resume."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["gameType"] != "sentence_builder":
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    # Fetch items in session order
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if session["itemOrder"]:
                placeholders = ",".join(["%s"] * len(session["itemOrder"]))
                await cur.execute(
                    f"""
                    SELECT id, lesson_id, exercise_data, topic_id, difficulty, hint
                    FROM lesson_exercises WHERE id IN ({placeholders})
                    """,
                    session["itemOrder"]
                )
                rows = await cur.fetchall()
                item_map = {row[0]: item_to_response(row, include_answer=True) for row in rows}
                items = [item_map[iid] for iid in session["itemOrder"] if iid in item_map]
            else:
                items = []
    
    return {
        "id": session["id"],
        "mode": session["mode"],
        "topicId": session["topicId"],
        "lessonId": session["lessonId"],
        "difficulty": session["difficulty"],
        "items": items,
        "progress": session["progress"],
        "startedAt": session["startedAt"],
        "completedAt": session["completedAt"]
    }


@router.post("/sessions/{session_id}/results")
async def record_sentence_result(
    session_id: str,
    payload: SentenceResult,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/sentence-builder/sessions/{sessionId}/results - Record a result."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    endpoint = f"/v1/sentence-builder/sessions/{session_id}/results"
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, endpoint, idempotency_key)
        if cached:
            return cached
    
    # Check clientResultId deduplication
    if payload.clientResultId:
        existing = await check_client_result_id(pool, session_id, payload.clientResultId)
        if existing:
            session = await dao.get_session(session_id)
            return {"ok": True, "progress": session["progress"], "item": existing}
    
    # Get session
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["status"] == "completed":
        raise_error(409, ErrorCodes.SESSION_COMPLETED, "Session already completed")
    
    # Validate item ID is in session
    if payload.itemId not in session["itemOrder"]:
        raise_error(400, ErrorCodes.UNKNOWN_ITEM, "Item not in session", {"invalidIds": [payload.itemId]})
    
    # Get accepted answers for validation
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT exercise_data FROM lesson_exercises WHERE id = %s",
                (payload.itemId,)
            )
            row = await cur.fetchone()
            if not row:
                raise_error(400, ErrorCodes.UNKNOWN_ITEM, "Item not found")
            
            exercise_data = row[0] if isinstance(row[0], dict) else json.loads(row[0]) if row[0] else {}
            accepted = exercise_data.get("accepted", [])
    
    # Server-side validation
    is_correct, error_type = check_sentence_answer(payload.userTokens, accepted)
    
    # Insert result
    await dao.insert_result(
        session_id=session_id,
        item_id=payload.itemId,
        is_correct=is_correct,
        attempts=payload.attempts,
        time_spent_ms=payload.timeSpentMs,
        user_tokens=payload.userTokens,
        error_type=error_type or payload.errorType,
        client_result_id=payload.clientResultId
    )
    
    # Update session progress
    progress = await dao.update_session_progress(session_id, is_correct, payload.itemId)
    
    # Track mistake if incorrect
    if not is_correct:
        await dao.record_mistake(
            user_id, "sentence_builder", payload.itemId,
            user_answer=json.dumps(payload.userTokens),
            correct_answer=json.dumps(accepted[0] if accepted else []),
            error_type=error_type
        )
    else:
        await dao.remove_mistake(user_id, "sentence_builder", payload.itemId)
    
    item_partial = {
        "id": payload.itemId,
        "lastTokens": payload.userTokens,
        "errorType": error_type,
        "attempts": payload.attempts
    }
    
    response = {"ok": True, "progress": progress, "item": item_partial}
    
    if idempotency_key:
        await store_idempotency(pool, user_id, endpoint, idempotency_key, response)
    
    return response


@router.post("/sessions/{session_id}/complete")
async def complete_sentence_session(
    session_id: str,
    payload: SentenceComplete = None,
    user=Depends(get_current_user)
):
    """POST /v1/sentence-builder/sessions/{sessionId}/complete - Complete a session."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["status"] == "completed":
        raise_error(409, ErrorCodes.SESSION_COMPLETED, "Session already completed")
    
    completed_session = await dao.complete_session(session_id)
    
    return {
        "id": completed_session["id"],
        "mode": completed_session["mode"],
        "topicId": completed_session["topicId"],
        "lessonId": completed_session["lessonId"],
        "items": [],
        "progress": completed_session["progress"],
        "masteredItemIds": completed_session["masteredIds"],
        "needsPracticeItemIds": completed_session["needsPracticeIds"],
        "startedAt": completed_session["startedAt"],
        "completedAt": completed_session["completedAt"]
    }


# =============================================================================
# Hint Endpoint
# =============================================================================

@router.get("/items/{item_id}/hint")
async def get_sentence_hint(
    item_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/sentence-builder/items/{itemId}/hint - Get hint for an item."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT hint, exercise_data FROM lesson_exercises WHERE id = %s",
                (item_id,)
            )
            row = await cur.fetchone()
            
            if not row:
                raise_error(404, ErrorCodes.UNKNOWN_ITEM, "Item not found")
            
            hint = row[0]
            if not hint:
                exercise_data = row[1] if isinstance(row[1], dict) else json.loads(row[1]) if row[1] else {}
                hint = exercise_data.get("hint", "No hint available for this item.")
    
    return {"itemId": item_id, "hint": hint}


# =============================================================================
# TTS Endpoint
# =============================================================================

@router.get("/items/{item_id}/tts")
async def get_sentence_tts(
    item_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/sentence-builder/items/{itemId}/tts - Get TTS audio URL for an item."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT exercise_data FROM lesson_exercises WHERE id = %s",
                (item_id,)
            )
            row = await cur.fetchone()
            
            if not row:
                raise_error(404, ErrorCodes.UNKNOWN_ITEM, "Item not found")
    
    # For now, return TTS type indicating client should use device TTS
    return {
        "itemId": item_id,
        "audioUrl": None,
        "language": "en-US",
        "audioType": "tts",
        "expiresAt": None
    }


# =============================================================================
# Mistakes Endpoint
# =============================================================================

@router.get("/mistakes")
async def get_sentence_mistakes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/sentence-builder/mistakes - Get user's sentence mistakes for review."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    mistakes, total = await dao.get_user_mistakes(user_id, "sentence_builder", page, limit)
    
    # Enrich with item data
    if mistakes:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                item_ids = [m["itemId"] for m in mistakes]
                placeholders = ",".join(["%s"] * len(item_ids))
                await cur.execute(
                    f"""
                    SELECT id, exercise_data, topic_id
                    FROM lesson_exercises WHERE id IN ({placeholders})
                    """,
                    item_ids
                )
                rows = await cur.fetchall()
                item_map = {}
                for row in rows:
                    exercise_data = row[1] if isinstance(row[1], dict) else json.loads(row[1]) if row[1] else {}
                    item_map[row[0]] = {
                        "english": exercise_data.get("english"),
                        "translation": exercise_data.get("translation"),
                        "topic": row[2]
                    }
                
                for m in mistakes:
                    i_data = item_map.get(m["itemId"], {})
                    m["english"] = i_data.get("english")
                    m["translation"] = i_data.get("translation")
                    m["topic"] = i_data.get("topic")
    
    return paginate(mistakes, page, limit, total)


# =============================================================================
# Stats Endpoint
# =============================================================================

@router.get("/stats/me")
async def get_sentence_stats(user=Depends(get_current_user)):
    """GET /v1/sentence-builder/stats/me - Get user's sentence statistics."""
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
                WHERE user_id = %s AND game_type = 'sentence_builder'
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
