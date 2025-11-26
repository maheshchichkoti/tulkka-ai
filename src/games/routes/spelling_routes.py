"""
Spelling Bee API Routes - TULKKA Games APIs Spec
Implements: Spelling Sessions, Pronunciations, Mistakes
"""

from fastapi import APIRouter, Depends, Request, Query, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import unicodedata

from src.games.middlewares.auth import get_current_user
from src.games.dao.games_dao import GamesDAO
from src.games.utils import (
    ErrorCodes, raise_error, paginate, ok_response,
    check_idempotency, store_idempotency, check_client_result_id
)
from src.db.mysql_pool import get_pool

router = APIRouter(prefix="/v1/spelling", tags=["Games - Spelling Bee"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class SpellingSessionStart(BaseModel):
    wordListId: str
    selectedWordIds: Optional[List[str]] = None
    shuffle: Optional[bool] = True
    prefetchAudio: Optional[bool] = False


class SpellingResult(BaseModel):
    clientResultId: Optional[str] = None
    wordId: str
    userAnswer: Optional[str] = None  # null when skipped
    isCorrect: bool
    attempts: int = Field(..., ge=0)
    timeSpentMs: int = Field(..., ge=0)
    skipped: Optional[bool] = False


class SpellingComplete(BaseModel):
    progress: Optional[dict] = None


# =============================================================================
# Helper Functions
# =============================================================================

async def get_pool_instance():
    """Get the MySQL connection pool."""
    return await get_pool()


def normalize_answer(text: str) -> str:
    """
    Normalize text for spelling comparison per spec:
    - Unicode NFC normalization
    - Trim whitespace
    - Collapse internal multiple spaces to single space
    - Case-insensitive (lowercase)
    """
    if not text:
        return ""
    # NFC normalization
    normalized = unicodedata.normalize('NFC', text)
    # Trim and collapse spaces
    normalized = ' '.join(normalized.split())
    # Lowercase
    return normalized.lower()


def check_spelling(user_answer: str, correct_word: str) -> bool:
    """Check if user's spelling is correct using normalization rules."""
    return normalize_answer(user_answer) == normalize_answer(correct_word)


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


# =============================================================================
# Session Endpoints
# =============================================================================

@router.post("/sessions", status_code=201)
async def start_spelling_session(
    payload: SpellingSessionStart,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/spelling/sessions - Start a new spelling session."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    
    # Check idempotency
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, "/v1/spelling/sessions", idempotency_key)
        if cached:
            return JSONResponse(status_code=201, content=cached)
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # Verify word list exists and belongs to user
            await cur.execute(
                "SELECT id FROM word_lists WHERE id = %s AND user_id = %s",
                (payload.wordListId, user_id)
            )
            if not await cur.fetchone():
                raise_error(404, ErrorCodes.WORD_LIST_NOT_FOUND, "Word list not found")
            
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
                
                # Check for invalid IDs
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
                    LIMIT 200
                    """,
                    (payload.wordListId,)
                )
                word_rows = await cur.fetchall()
            
            if not word_rows:
                raise_error(400, ErrorCodes.VALIDATION_ERROR, "No words available for practice")
            
            words = [word_to_response(row) for row in word_rows]
            word_ids = [w["id"] for w in words]
    
    # Create session
    dao = GamesDAO(pool)
    session = await dao.create_session(
        user_id=user_id,
        game_type="spelling_bee",
        item_ids=word_ids,
        shuffle=payload.shuffle if payload.shuffle is not None else True,
        word_list_id=payload.wordListId,
        mode="custom" if payload.selectedWordIds else "topic"
    )
    
    # Reorder words to match session order
    word_map = {w["id"]: w for w in words}
    ordered_words = [word_map[wid] for wid in session["itemOrder"] if wid in word_map]
    
    response = {
        "id": session["id"],
        "wordListId": payload.wordListId,
        "words": ordered_words,
        "progress": session["progress"],
        "startedAt": session["startedAt"],
        "completedAt": None
    }
    
    if idempotency_key:
        await store_idempotency(pool, user_id, "/v1/spelling/sessions", idempotency_key, response)
    
    return JSONResponse(
        status_code=201,
        content=response,
        headers={"Location": f"/v1/spelling/sessions/{session['id']}"}
    )


@router.get("/sessions/{session_id}")
async def get_spelling_session(
    session_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/spelling/sessions/{sessionId} - Get session state for resume."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    session = await dao.get_session(session_id)
    if not session or session["userId"] != user_id:
        raise_error(404, ErrorCodes.SESSION_NOT_FOUND, "Session not found")
    
    if session["gameType"] != "spelling_bee":
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


@router.post("/sessions/{session_id}/results")
async def record_spelling_result(
    session_id: str,
    payload: SpellingResult,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user=Depends(get_current_user)
):
    """POST /v1/spelling/sessions/{sessionId}/results - Record a spelling result."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    # Check idempotency
    endpoint = f"/v1/spelling/sessions/{session_id}/results"
    if idempotency_key:
        cached = await check_idempotency(pool, user_id, endpoint, idempotency_key)
        if cached:
            return cached
    
    # Check clientResultId deduplication
    if payload.clientResultId:
        existing = await check_client_result_id(pool, session_id, payload.clientResultId)
        if existing:
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
    
    # Get the correct word for validation
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT word FROM words WHERE id = %s", (payload.wordId,))
            word_row = await cur.fetchone()
            if not word_row:
                raise_error(400, ErrorCodes.UNKNOWN_WORD, "Word not found")
            correct_word = word_row[0]
    
    # Server-side validation of correctness (if userAnswer provided)
    is_correct = payload.isCorrect
    if payload.userAnswer and not payload.skipped:
        is_correct = check_spelling(payload.userAnswer, correct_word)
    
    # Insert result
    await dao.insert_result(
        session_id=session_id,
        item_id=payload.wordId,
        is_correct=is_correct,
        attempts=payload.attempts,
        time_spent_ms=payload.timeSpentMs,
        skipped=payload.skipped or False,
        user_answer=payload.userAnswer,
        client_result_id=payload.clientResultId
    )
    
    # Update session progress
    progress = await dao.update_session_progress(session_id, is_correct, payload.wordId)
    
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
                (1 if is_correct else 0, 1 if is_correct else 0, payload.wordId)
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
    if not is_correct:
        await dao.record_mistake(
            user_id, "spelling_bee", payload.wordId,
            user_answer=payload.userAnswer,
            correct_answer=correct_word
        )
    else:
        await dao.remove_mistake(user_id, "spelling_bee", payload.wordId)
    
    word_partial = {
        "id": word_row[0],
        "practiceCount": word_row[5],
        "correctCount": word_row[6],
        "accuracy": word_row[7],
        "lastPracticed": word_row[8].isoformat() + "Z" if word_row[8] else None
    }
    
    response = {"ok": True, "progress": progress, "word": word_partial}
    
    if idempotency_key:
        await store_idempotency(pool, user_id, endpoint, idempotency_key, response)
    
    return response


@router.post("/sessions/{session_id}/complete")
async def complete_spelling_session(
    session_id: str,
    payload: SpellingComplete = None,
    user=Depends(get_current_user)
):
    """POST /v1/spelling/sessions/{sessionId}/complete - Complete a session."""
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
        "wordListId": completed_session["wordListId"],
        "words": [],
        "progress": completed_session["progress"],
        "masteredWordIds": completed_session["masteredIds"],
        "needsPracticeWordIds": completed_session["needsPracticeIds"],
        "startedAt": completed_session["startedAt"],
        "completedAt": completed_session["completedAt"]
    }


# =============================================================================
# Pronunciation Endpoint
# =============================================================================

@router.get("/pronunciations/{word_id}")
async def get_pronunciation(
    word_id: str,
    user=Depends(get_current_user)
):
    """GET /v1/spelling/pronunciations/{wordId} - Get pronunciation audio URL."""
    pool = await get_pool_instance()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, word FROM words WHERE id = %s", (word_id,))
            row = await cur.fetchone()
            
            if not row:
                raise_error(404, ErrorCodes.UNKNOWN_WORD, "Word not found")
    
    # For now, return TTS type indicating client should use device TTS
    # In production, this could return pre-generated audio URLs
    return {
        "wordId": word_id,
        "audioUrl": None,  # No pre-generated audio
        "language": "en-US",
        "audioType": "tts",  # Client should use device TTS
        "expiresAt": None,
        "contentLength": None
    }


# =============================================================================
# Mistakes Endpoint
# =============================================================================

@router.get("/mistakes")
async def get_spelling_mistakes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    """GET /v1/spelling/mistakes - Get user's spelling mistakes for review."""
    pool = await get_pool_instance()
    user_id = user["userId"]
    dao = GamesDAO(pool)
    
    mistakes, total = await dao.get_user_mistakes(user_id, "spelling_bee", page, limit)
    
    # Enrich with word data
    if mistakes:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                item_ids = [m["itemId"] for m in mistakes]
                placeholders = ",".join(["%s"] * len(item_ids))
                await cur.execute(
                    f"SELECT id, word, translation FROM words WHERE id IN ({placeholders})",
                    item_ids
                )
                word_rows = await cur.fetchall()
                word_map = {row[0]: {"word": row[1], "translation": row[2]} for row in word_rows}
                
                for m in mistakes:
                    word_data = word_map.get(m["itemId"], {})
                    m["word"] = word_data.get("word")
                    m["translation"] = word_data.get("translation")
    
    return paginate(mistakes, page, limit, total)


# =============================================================================
# Stats Endpoint
# =============================================================================

@router.get("/stats/me")
async def get_spelling_stats(user=Depends(get_current_user)):
    """GET /v1/spelling/stats/me - Get user's spelling statistics."""
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
                WHERE user_id = %s AND game_type = 'spelling_bee'
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
