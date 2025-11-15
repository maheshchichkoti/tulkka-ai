# src/games/routes/sentence_routes.py
"""Sentence builder game routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from src.games.middlewares.auth import get_current_user
from src.db.mysql_pool import execute_query

router = APIRouter(prefix="/v1/sentence", tags=["Games - Sentence Builder"])

@router.get("/lessons")
async def get_sentence_lessons(class_id: str, user=Depends(get_current_user)):
    """Get available sentence lessons"""
    q = """
    SELECT DISTINCT l.lesson_number, l.created_at
    FROM lessons l
    WHERE l.class_id = %s
    ORDER BY l.lesson_number DESC
    """
    lessons = await execute_query(q, (class_id,), fetchall=True)
    return {"lessons": lessons or []}

@router.get("/sessions/{session_id}")
async def get_sentence_session(session_id: str, user=Depends(get_current_user)):
    """Get sentence session details"""
    q = "SELECT * FROM sentence_sessions WHERE id = %s AND user_id = %s"
    session = await execute_query(q, (session_id, user['userId']), fetchone=True)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@router.post("/sessions")
async def start_sentence_session(lesson_number: int, class_id: str, user=Depends(get_current_user)):
    """Start a new sentence builder session"""
    from uuid import uuid4
    session_id = f"sb_{uuid4().hex}"
    
    q = """
    INSERT INTO sentence_sessions (id, user_id, class_id, lesson_number, started_at, status)
    VALUES (%s, %s, %s, %s, UTC_TIMESTAMP(), 'active')
    """
    await execute_query(q, (session_id, user['userId'], class_id, lesson_number))
    
    return {"id": session_id, "status": "active"}

@router.post("/sessions/{session_id}/results")
async def record_sentence_result(session_id: str, item_id: str, is_correct: bool, user=Depends(get_current_user)):
    """Record sentence result"""
    q = """
    INSERT INTO sentence_results (id, session_id, item_id, is_correct, created_at)
    VALUES (UUID(), %s, %s, %s, UTC_TIMESTAMP())
    """
    await execute_query(q, (session_id, item_id, int(is_correct)))
    
    return {"ok": True}

@router.get("/stats/me")
async def get_sentence_stats(user=Depends(get_current_user)):
    """Get user sentence statistics"""
    q = """
    SELECT COUNT(*) as total_sessions,
           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions
    FROM sentence_sessions
    WHERE user_id = %s
    """
    stats = await execute_query(q, (user['userId'],), fetchone=True)
    return stats or {"total_sessions": 0, "completed_sessions": 0}
