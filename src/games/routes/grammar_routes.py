# src/games/routes/grammar_routes.py
"""Grammar challenge game routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from src.games.middlewares.auth import get_current_user
from src.db.mysql_pool import execute_query

router = APIRouter(prefix="/v1/grammar", tags=["Games - Grammar"])

@router.get("/lessons")
async def get_grammar_lessons(class_id: str, user=Depends(get_current_user)):
    """Get available grammar lessons"""
    q = """
    SELECT DISTINCT l.lesson_number, l.created_at
    FROM lessons l
    WHERE l.class_id = %s
    ORDER BY l.lesson_number DESC
    """
    lessons = await execute_query(q, (class_id,), fetchall=True)
    return {"lessons": lessons or []}

@router.get("/sessions/{session_id}")
async def get_grammar_session(session_id: str, user=Depends(get_current_user)):
    """Get grammar session details"""
    q = "SELECT * FROM grammar_sessions WHERE id = %s AND user_id = %s"
    session = await execute_query(q, (session_id, user['userId']), fetchone=True)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@router.post("/sessions")
async def start_grammar_session(lesson_number: int, class_id: str, user=Depends(get_current_user)):
    """Start a new grammar session"""
    from uuid import uuid4
    session_id = f"gr_{uuid4().hex}"
    
    q = """
    INSERT INTO grammar_sessions (id, user_id, class_id, lesson_number, started_at, status)
    VALUES (%s, %s, %s, %s, UTC_TIMESTAMP(), 'active')
    """
    await execute_query(q, (session_id, user['userId'], class_id, lesson_number))
    
    return {"id": session_id, "status": "active"}

@router.post("/sessions/{session_id}/results")
async def record_grammar_result(session_id: str, question_id: str, is_correct: bool, user=Depends(get_current_user)):
    """Record grammar result"""
    q = """
    INSERT INTO grammar_results (id, session_id, question_id, is_correct, created_at)
    VALUES (UUID(), %s, %s, %s, UTC_TIMESTAMP())
    """
    await execute_query(q, (session_id, question_id, int(is_correct)))
    
    return {"ok": True}

@router.get("/stats/me")
async def get_grammar_stats(user=Depends(get_current_user)):
    """Get user grammar statistics"""
    q = """
    SELECT COUNT(*) as total_sessions,
           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions
    FROM grammar_sessions
    WHERE user_id = %s
    """
    stats = await execute_query(q, (user['userId'],), fetchone=True)
    return stats or {"total_sessions": 0, "completed_sessions": 0}
