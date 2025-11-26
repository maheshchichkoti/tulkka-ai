"""
Advanced Cloze API Routes - TULKKA Games APIs Spec
Implements: Topics, Lessons, Items, Sessions, Hints, Mistakes
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

router = APIRouter(prefix="/v1/advanced-cloze", tags=["Games - Advanced Cloze"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ClozeSessionStart(BaseModel):
    mode: Literal["topic", "lesson", "custom", "mistakes"]
    topicId: Optional[str] = None
    lessonId: Optional[str] = None
    selectedItemIds: Optional[List[str]] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    limit: Optional[int] = Field(None, ge=1, le=50)
    shuffle: Optional[bool] = True


class ClozeResult(BaseModel):
    clientResultId: Optional[str] = None
    itemId: str
    selectedAnswers: List[str]
    isCorrect: bool
    attempts: int = Field(..., ge=0)
    timeSpentMs: int = Field(..., ge=0)


class ClozeComplete(BaseModel):
    progress: Optional[dict] = None


# =============================================================================
# Helper Functions
# =============================================================================

async def get_pool_instance():
    """Get the MySQL connection pool."""
    return await get_pool()


def item_to_response(row: tuple, include_answer: bool = False) -> dict:
    """Convert a lesson_exercises row to Cloze Item format."""
    exercise_data = row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {}
    
    response = {
        "id": row[0],
        "textParts": exercise_data.get("textParts", []),
        "options": exercise_data.get("options", []),
        "topic": row[3] or exercise_data.get("topic"),
        "difficulty": row[4] or exercise_data.get("difficulty", "medium"),
    }
    
    if include_answer:
        response["correct"] = exercise_data.get("correct", [])
        response["explanation"] = exercise_data.get("explanation", "")
    
    return response


# =============================================================================
# Catalog Endpoints
# =============================================================================

@router.get("/topics")
async def get_cloze_topics(
    user=Depends(get_current_user)
):
    """GET /v1/advanced-cloze/topics - Get available cloze topics."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT DISTINCT topic_id, topic_name, COUNT(*) as itemCount
                FROM lesson_exercises
                WHERE exercise_type = 'cloze' AND status = 'approved'
                GROUP BY topic_id, topic_name
                ORDER BY topic_name
                """
            )
            rows = await cur.fetchall()
    
    topics = []
    for row in rows:
        topics.append({
            "id": row[0] or "general",
            "name": row[1] or "General Cloze",
            "itemCount": row[2]
        })
    
    return {"data": topics}


@router.get("/lessons")
async def get_cloze_lessons(
    topicId: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/advanced-cloze/lessons - Get cloze lessons."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            where_clauses = ["le.exercise_type = 'cloze'", "le.status = 'approved'"]
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
async def get_cloze_items(
    topicId: Optional[str] = None,
    lessonId: Optional[str] = None,
    difficulty: Optional[str] = None,
    include: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/advanced-cloze/items - Get cloze items catalog."""
    pool = await get_pool_instance()
    include_answer = include and ("options" in include or "explanation" in include)
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            where_clauses = ["exercise_type = 'cloze'", "status = 'approved'"]
            params = []
            
            if topicId:
                where_clauses.append("topic_id = %s")
                params.append(topicId)
            
            if lessonId:
                where_clauses.append("lesson_id = %s")
                params.append(lessonId)
            
            if difficulty:
                where_clauses.append("difficulty = %s")
                params.append(difficulty)
            
            where_sql = " AND ".join(where_clauses)
            
            # Get total
            await cur.execute(f"SELECT COUNT(*) FROM lesson_exercises WHERE {where_sql}", params)
            total = (await cur.fetchone())[0]
            
            # Get paginated items
            offset = (page - 1) * limit
            await cur.execute(
                f"""
                SELECT id, lesson_id, exercise_data, topic_id, difficulty, hint
                FROM lesson_exercises
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset]
            )
            rows = await cur.fetchall()
    
    items = [item_to_response(row, include_answer) for row in rows]
    return paginate(items, page, limit, total)


# =============================================================================
# Session Endpoints
# =============================================================================

@router.post("/sessions", status_code=201)
async def start_cloze_session(
    payload: ClozeSessionStart,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/advanced-cloze/sessions - Start a new cloze session."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, "/v1/advanced-cloze/sessions", idempotency_key)
        if cached:
            return JSONResponse(status_code=201, content=cached)
    
    items = []
    item_ids = []
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if payload.mode == "custom" and payload.selectedItemIds:
                # Custom mode
                placeholders = ",".join(["%s"] * len(payload.selectedItemIds))
                await cur.execute(
                    f"""
                    SELECT id, lesson_id, exercise_data, topic_id, difficulty, hint
                    FROM lesson_exercises
                    WHERE id IN ({placeholders}) AND exercise_type = 'cloze' AND status = 'approved'
                    """,
                    payload.selectedItemIds
                )
                rows = await cur.fetchall()
                
                found_ids = {row[0] for row in rows}
                invalid_ids = [iid for iid in payload.selectedItemIds if iid not in found_ids]
                if invalid_ids:
                    raise_error(400, ErrorCodes.UNKNOWN_ITEM, "Unknown item IDs", {"invalidIds": invalid_ids})
                
            elif payload.mode == "mistakes":
                mistake_ids = await dao.get_mistake_item_ids(user_id, "advanced_cloze", payload.limit or 20)
                if not mistake_ids:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "No mistakes to review")
                
                placeholders = ",".join(["%s"] * len(mistake_ids))
                await cur.execute(
                    f"""
                    SELECT id, lesson_id, exercise_data, topic_id, difficulty, hint
                    FROM lesson_exercises
                    WHERE id IN ({placeholders}) AND exercise_type = 'cloze'
                    """,
                    mistake_ids
                )
                rows = await cur.fetchall()
                
            elif payload.mode == "lesson" and payload.lessonId:
                await cur.execute(
                    """
                    SELECT id, lesson_id, exercise_data, topic_id, difficulty, hint
                    FROM lesson_exercises
                    WHERE lesson_id = %s AND exercise_type = 'cloze' AND status = 'approved'
                    ORDER BY created_at
                    LIMIT %s
                    """,
                    (payload.lessonId, payload.limit or 20)
                )
                rows = await cur.fetchall()
                
            else:
                # Topic mode (default)
                where_clauses = ["exercise_type = 'cloze'", "status = 'approved'"]
                params = []
                
                if payload.topicId:
                    where_clauses.append("topic_id = %s")
                    params.append(payload.topicId)
                
                if payload.difficulty:
                    where_clauses.append("difficulty = %s")
                    params.append(payload.difficulty)
                
                where_sql = " AND ".join(where_clauses)
                params.append(payload.limit or 20)
                
                await cur.execute(
                    f"""
                    SELECT id, lesson_id, exercise_data, topic_id, difficulty, hint
                    FROM lesson_exercises
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
        game_type="advanced_cloze",
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
        await store_idempotency(pool, user_id, "/v1/advanced-cloze/sessions", idempotency_key, response)
    
    return JSONResponse(
        status_code=201,
        content=response,
        headers={"Location": f"/v1/advanced-cloze/sessions/{session['id']}"}
    )


@router.get("/sessions/{session_id}")
async def get_cloze_session(
    session_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/advanced-cloze/sessions/{sessionId} - Get session state for resume."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["gameType"] != "advanced_cloze":
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
async def record_cloze_result(
    session_id: str,
    payload: ClozeResult,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/advanced-cloze/sessions/{sessionId}/results - Record a result."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    endpoint = f"/v1/advanced-cloze/sessions/{session_id}/results"
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
    
    # Get correct answers for validation
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
            correct_answers = exercise_data.get("correct", [])
    
    # Server-side validation
    is_correct = payload.selectedAnswers == correct_answers
    
    # Insert result
    await dao.insert_result(
        session_id=session_id,
        item_id=payload.itemId,
        is_correct=is_correct,
        attempts=payload.attempts,
        time_spent_ms=payload.timeSpentMs,
        selected_answers=payload.selectedAnswers,
        client_result_id=payload.clientResultId
    )
    
    # Update session progress
    progress = await dao.update_session_progress(session_id, is_correct, payload.itemId)
    
    # Track mistake if incorrect
    if not is_correct:
        await dao.record_mistake(
            user_id, "advanced_cloze", payload.itemId,
            selected_answers=payload.selectedAnswers,
            correct_answer=json.dumps(correct_answers)
        )
    else:
        await dao.remove_mistake(user_id, "advanced_cloze", payload.itemId)
    
    item_partial = {
        "id": payload.itemId,
        "lastSelected": payload.selectedAnswers,
        "attempts": payload.attempts
    }
    
    response = {"ok": True, "progress": progress, "item": item_partial}
    
    if idempotency_key:
        await store_idempotency(pool, user_id, endpoint, idempotency_key, response)
    
    return response


@router.post("/sessions/{session_id}/complete")
async def complete_cloze_session(
    session_id: str,
    payload: ClozeComplete = None,
    user=Depends(get_current_user)
):
    """POST /v1/advanced-cloze/sessions/{sessionId}/complete - Complete a session."""
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
async def get_cloze_hint(
    item_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/advanced-cloze/items/{itemId}/hint - Get hint for an item."""
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
# Mistakes Endpoint
# =============================================================================

@router.get("/mistakes")
async def get_cloze_mistakes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/advanced-cloze/mistakes - Get user's cloze mistakes for review."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    mistakes, total = await dao.get_user_mistakes(user_id, "advanced_cloze", page, limit)
    
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
                        "textParts": exercise_data.get("textParts"),
                        "topic": row[2]
                    }
                
                for m in mistakes:
                    i_data = item_map.get(m["itemId"], {})
                    m["textParts"] = i_data.get("textParts")
                    m["topic"] = i_data.get("topic")
    
    return paginate(mistakes, page, limit, total)


# =============================================================================
# Stats Endpoint
# =============================================================================

@router.get("/stats/me")
async def get_cloze_stats(user=Depends(get_current_user)):
    """GET /v1/advanced-cloze/stats/me - Get user's cloze statistics."""
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
                WHERE user_id = %s AND game_type = 'advanced_cloze'
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
