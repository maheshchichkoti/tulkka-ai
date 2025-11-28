"""
Grammar Challenge API Routes - TULKKA Games APIs Spec
Implements: Categories, Lessons, Questions, Sessions, Hints, Mistakes
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

router = APIRouter(prefix="/v1/grammar-challenge", tags=["Games - Grammar Challenge"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class GrammarSessionStart(BaseModel):
    mode: Literal["topic", "lesson", "custom", "mistakes"]
    categoryId: Optional[str] = None
    lessonId: Optional[str] = None
    selectedQuestionIds: Optional[List[str]] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    limit: Optional[int] = Field(None, ge=1, le=50)
    shuffle: Optional[bool] = True


class GrammarResult(BaseModel):
    clientResultId: Optional[str] = None
    questionId: str
    selectedAnswer: int = Field(..., ge=0)
    isCorrect: bool
    attempts: int = Field(..., ge=0)
    timeSpentMs: int = Field(..., ge=0)


class GrammarSkip(BaseModel):
    questionId: str


class GrammarComplete(BaseModel):
    progress: Optional[dict] = None


# =============================================================================
# Helper Functions
# =============================================================================

async def get_pool_instance():
    """Get the MySQL connection pool."""
    return await get_pool()


def question_to_response(row: tuple, include_answer: bool = False) -> dict:
    """Convert a lesson_exercises row to Grammar Question format."""
    exercise_data = row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {}
    
    response = {
        "id": row[0],
        "prompt": exercise_data.get("prompt", ""),
        "options": exercise_data.get("options", []),
        "category": row[3] or exercise_data.get("category"),
        "difficulty": row[4] or exercise_data.get("difficulty", "medium"),
    }
    
    if include_answer:
        response["correctIndex"] = exercise_data.get("correctIndex", 0)
        response["explanation"] = exercise_data.get("explanation", "")
    
    return response


# =============================================================================
# Catalog Endpoints
# =============================================================================

@router.get("/categories")
async def get_grammar_categories(
    user=Depends(get_current_user)
):
    """GET /v1/grammar-challenge/categories - Get available grammar categories."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT DISTINCT le.topic_id, le.topic_name, COUNT(*) as questionCount
                FROM lesson_exercises le
                JOIN lessons l ON l.id = le.lesson_id
                WHERE le.exercise_type = 'grammar_challenge' AND l.status = 'approved'
                GROUP BY le.topic_id, le.topic_name
                ORDER BY le.topic_name
                """
            )
            rows = await cur.fetchall()
    
    categories = []
    for row in rows:
        categories.append({
            "id": row[0] or "general",
            "name": row[1] or "General Grammar",
            "questionCount": row[2]
        })
    
    return {"data": categories}


@router.get("/lessons")
async def get_grammar_lessons(
    categoryId: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/grammar-challenge/lessons - Get grammar lessons."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            where_clauses = ["le.exercise_type = 'grammar_challenge'", "l.status = 'approved'"]
            params = []
            
            if categoryId:
                where_clauses.append("le.topic_id = %s")
                params.append(categoryId)
            
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
                       COUNT(le.id) as questionCount
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
            "questionCount": row[5],
            "createdAt": row[4].isoformat() + "Z" if row[4] else None
        })
    
    return paginate(lessons, page, limit, total)


@router.get("/questions")
async def get_grammar_questions(
    categoryId: Optional[str] = None,
    lessonId: Optional[str] = None,
    difficulty: Optional[str] = None,
    include: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/grammar-challenge/questions - Get grammar questions catalog."""
    pool = await get_pool_instance()
    include_answer = include and ("options" in include or "explanation" in include)
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            where_clauses = ["le.exercise_type = 'grammar_challenge'", "l.status = 'approved'"]
            params = []
            
            if categoryId:
                where_clauses.append("le.topic_id = %s")
                params.append(categoryId)
            
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
            
            # Get paginated questions
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
    
    questions = [question_to_response(row, include_answer) for row in rows]
    return paginate(questions, page, limit, total)


# =============================================================================
# Session Endpoints
# =============================================================================
@router.post("/sessions", status_code=201)
async def start_grammar_session(
    payload: GrammarSessionStart,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/grammar-challenge/sessions - Start a new grammar session."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, "/v1/grammar-challenge/sessions", idempotency_key)
        if cached:
            return JSONResponse(status_code=201, content=cached)
    
    questions = []
    question_ids = []
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if payload.mode == "custom" and payload.selectedQuestionIds:
                # Custom mode: use selected question IDs
                placeholders = ",".join(["%s"] * len(payload.selectedQuestionIds))
                await cur.execute(
                    f"""
                    SELECT le.id, le.lesson_id, le.exercise_data, le.topic_id, le.difficulty, le.hint
                    FROM lesson_exercises le
                    JOIN lessons l ON l.id = le.lesson_id
                    WHERE le.id IN ({placeholders})
                      AND le.exercise_type = 'grammar_challenge'
                      AND l.status = 'approved'
                    """,
                    payload.selectedQuestionIds
                )
                rows = await cur.fetchall()
                
                # Validate all IDs exist
                found_ids = {row[0] for row in rows}
                invalid_ids = [qid for qid in payload.selectedQuestionIds if qid not in found_ids]
                if invalid_ids:
                    raise_error(400, ErrorCodes.UNKNOWN_QUESTION, "Unknown question IDs", {"invalidIds": invalid_ids})
                
            elif payload.mode == "mistakes":
                # Mistakes mode: get user's mistake items
                mistake_ids = await dao.get_mistake_item_ids(user_id, "grammar_challenge", payload.limit or 20)
                if not mistake_ids:
                    raise_error(400, ErrorCodes.VALIDATION_ERROR, "No mistakes to review")
                
                placeholders = ",".join(["%s"] * len(mistake_ids))
                await cur.execute(
                    f"""
                    SELECT le.id, le.lesson_id, le.exercise_data, le.topic_id, le.difficulty, le.hint
                    FROM lesson_exercises le
                    JOIN lessons l ON l.id = le.lesson_id
                    WHERE le.id IN ({placeholders})
                      AND le.exercise_type = 'grammar_challenge'
                      AND l.status = 'approved'
                    """,
                    mistake_ids
                )
                rows = await cur.fetchall()
                
            elif payload.mode == "lesson" and payload.lessonId:
                # Lesson mode
                await cur.execute(
                    """
                    SELECT le.id, le.lesson_id, le.exercise_data, le.topic_id, le.difficulty, le.hint
                    FROM lesson_exercises le
                    JOIN lessons l ON l.id = le.lesson_id
                    WHERE le.lesson_id = %s
                      AND le.exercise_type = 'grammar_challenge'
                      AND l.status = 'approved'
                    ORDER BY le.created_at
                    LIMIT %s
                    """,
                    (payload.lessonId, payload.limit or 20)
                )
                rows = await cur.fetchall()
                
            else:
                # Topic mode (default)
                where_clauses = ["le.exercise_type = 'grammar_challenge'", "l.status = 'approved'"]
                params = []
                
                if payload.categoryId:
                    where_clauses.append("le.topic_id = %s")
                    params.append(payload.categoryId)
                
                if payload.difficulty:
                    where_clauses.append("le.difficulty = %s")
                    params.append(payload.difficulty)
                
                where_sql = " AND ".join(where_clauses)
                params.append(payload.limit or 20)
                
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
                raise_error(400, ErrorCodes.VALIDATION_ERROR, "No questions available")
            
            questions = [question_to_response(row, include_answer=True) for row in rows]
            question_ids = [q["id"] for q in questions]
    
    # Create session
    session = await dao.create_session(
        user_id=user_id,
        game_type="grammar_challenge",
        item_ids=question_ids,
        shuffle=payload.shuffle if payload.shuffle is not None else True,
        category_id=payload.categoryId,
        lesson_id=payload.lessonId,
        mode=payload.mode,
        difficulty=payload.difficulty
    )
    
    # Reorder questions to match session order
    question_map = {q["id"]: q for q in questions}
    ordered_questions = [question_map[qid] for qid in session["itemOrder"] if qid in question_map]
    
    response = {
        "id": session["id"],
        "mode": payload.mode,
        "categoryId": payload.categoryId,
        "lessonId": payload.lessonId,
        "difficulty": payload.difficulty,
        "questions": ordered_questions,
        "progress": session["progress"],
        "startedAt": session["startedAt"],
        "completedAt": None
    }
    
    if idempotency_key:
        await store_idempotency(pool, user_id, "/v1/grammar-challenge/sessions", idempotency_key, response)
    
    return JSONResponse(
        status_code=201,
        content=response,
        headers={"Location": f"/v1/grammar-challenge/sessions/{session['id']}"}
    )


@router.get("/sessions/{session_id}")
async def get_grammar_session(
    session_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/grammar-challenge/sessions/{sessionId} - Get session state for resume."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["gameType"] != "grammar_challenge":
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    # Fetch questions in session order
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
                question_map = {row[0]: question_to_response(row, include_answer=True) for row in rows}
                questions = [question_map[qid] for qid in session["itemOrder"] if qid in question_map]
            else:
                questions = []
    
    return {
        "id": session["id"],
        "mode": session["mode"],
        "categoryId": session["categoryId"],
        "lessonId": session["lessonId"],
        "difficulty": session["difficulty"],
        "questions": questions,
        "progress": session["progress"],
        "startedAt": session["startedAt"],
        "completedAt": session["completedAt"]
    }


@router.post("/sessions/{session_id}/results")
async def record_grammar_result(
    session_id: str,
    payload: GrammarResult,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/grammar-challenge/sessions/{sessionId}/results - Record a result."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    endpoint = f"/v1/grammar-challenge/sessions/{session_id}/results"
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, endpoint, idempotency_key)
        if cached:
            return cached
    
    # Check clientResultId deduplication
    if payload.clientResultId:
        existing = await check_client_result_id(pool, session_id, payload.clientResultId)
        if existing:
            session = await dao.get_session(session_id)
            return {"ok": True, "progress": session["progress"], "question": existing}
    
    # Get session
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["status"] == "completed":
        raise_error(409, ErrorCodes.SESSION_COMPLETED, "Session already completed")
    
    # Validate question ID is in session
    if payload.questionId not in session["itemOrder"]:
        raise_error(400, ErrorCodes.UNKNOWN_QUESTION, "Question not in session", {"invalidIds": [payload.questionId]})
    
    # Get correct answer for validation
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT exercise_data FROM lesson_exercises WHERE id = %s",
                (payload.questionId,)
            )
            row = await cur.fetchone()
            if not row:
                raise_error(400, ErrorCodes.UNKNOWN_QUESTION, "Question not found")
            
            exercise_data = row[0] if isinstance(row[0], dict) else json.loads(row[0]) if row[0] else {}
            correct_index = exercise_data.get("correctIndex", 0)
    
    # Server-side validation
    is_correct = payload.selectedAnswer == correct_index
    
    # Insert result
    await dao.insert_result(
        session_id=session_id,
        item_id=payload.questionId,
        is_correct=is_correct,
        attempts=payload.attempts,
        time_spent_ms=payload.timeSpentMs,
        selected_answer=payload.selectedAnswer,
        client_result_id=payload.clientResultId
    )
    
    # Update session progress
    progress = await dao.update_session_progress(session_id, is_correct, payload.questionId)
    
    # Track mistake if incorrect
    if not is_correct:
        await dao.record_mistake(user_id, "grammar_challenge", payload.questionId)
    else:
        await dao.remove_mistake(user_id, "grammar_challenge", payload.questionId)
    
    question_partial = {
        "id": payload.questionId,
        "lastSelected": payload.selectedAnswer,
        "attempts": payload.attempts
    }
    
    response = {"ok": True, "progress": progress, "question": question_partial}
    
    if idempotency_key:
        await store_idempotency(pool, user_id, endpoint, idempotency_key, response)
    
    return response


@router.post("/sessions/{session_id}/skip")
async def skip_grammar_question(
    session_id: str,
    payload: GrammarSkip,
    user=Depends(get_current_user)
):
    """POST /v1/grammar-challenge/sessions/{sessionId}/skip - Skip a question."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["status"] == "completed":
        raise_error(409, ErrorCodes.SESSION_COMPLETED, "Session already completed")
    
    if payload.questionId not in session["itemOrder"]:
        raise_error(400, ErrorCodes.UNKNOWN_QUESTION, "Question not in session")
    
    # Insert skip result (attempts=0)
    await dao.insert_result(
        session_id=session_id,
        item_id=payload.questionId,
        is_correct=False,
        attempts=0,
        time_spent_ms=0,
        skipped=True
    )
    
    # Update progress (skipped counts as incorrect)
    progress = await dao.update_session_progress(session_id, False, payload.questionId)
    
    return {"ok": True, "progress": progress}


@router.post("/sessions/{session_id}/complete")
async def complete_grammar_session(
    session_id: str,
    payload: GrammarComplete = None,
    user=Depends(get_current_user)
):
    """POST /v1/grammar-challenge/sessions/{sessionId}/complete - Complete a session."""
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
        "categoryId": completed_session["categoryId"],
        "lessonId": completed_session["lessonId"],
        "questions": [],
        "progress": completed_session["progress"],
        "masteredQuestionIds": completed_session["masteredIds"],
        "needsPracticeQuestionIds": completed_session["needsPracticeIds"],
        "startedAt": completed_session["startedAt"],
        "completedAt": completed_session["completedAt"]
    }


# =============================================================================
# Hint Endpoint
# =============================================================================

@router.get("/questions/{question_id}/hint")
async def get_grammar_hint(
    question_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/grammar-challenge/questions/{questionId}/hint - Get hint for a question."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT hint, exercise_data FROM lesson_exercises WHERE id = %s",
                (question_id,)
            )
            row = await cur.fetchone()
            
            if not row:
                raise_error(404, ErrorCodes.UNKNOWN_QUESTION, "Question not found")
            
            hint = row[0]
            if not hint:
                # Try to get hint from exercise_data
                exercise_data = row[1] if isinstance(row[1], dict) else json.loads(row[1]) if row[1] else {}
                hint = exercise_data.get("hint", "No hint available for this question.")
    
    return {"questionId": question_id, "hint": hint}


# =============================================================================
# Mistakes Endpoint
# =============================================================================

@router.get("/mistakes")
async def get_grammar_mistakes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/grammar-challenge/mistakes - Get user's grammar mistakes for review."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    mistakes, total = await dao.get_user_mistakes(user_id, "grammar_challenge", page, limit)
    
    # Enrich with question data
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
                question_map = {}
                for row in rows:
                    exercise_data = row[1] if isinstance(row[1], dict) else json.loads(row[1]) if row[1] else {}
                    question_map[row[0]] = {
                        "prompt": exercise_data.get("prompt"),
                        "category": row[2]
                    }
                
                for m in mistakes:
                    q_data = question_map.get(m["itemId"], {})
                    m["prompt"] = q_data.get("prompt")
                    m["category"] = q_data.get("category")
    
    return paginate(mistakes, page, limit, total)


# =============================================================================
# Stats Endpoint
# =============================================================================

@router.get("/stats/me")
async def get_grammar_stats(user=Depends(get_current_user)):
    """GET /v1/grammar-challenge/stats/me - Get user's grammar statistics."""
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
                WHERE user_id = %s AND game_type = 'grammar_challenge'
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
