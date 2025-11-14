# src/games/routes/spelling_routes.py
"""Spelling game routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from src.games.middlewares.auth import get_current_user
from src.db.mysql_pool import execute_query

router = APIRouter(prefix="/v1/spelling", tags=["Games - Spelling"])

@router.get("/sessions/{session_id}")
async def get_spelling_session(session_id: str, user=Depends(get_current_user)):
    """Get spelling session details"""
    q = "SELECT * FROM spelling_sessions WHERE id = %s AND user_id = %s"
    session = await execute_query(q, (session_id, user['userId']), fetchone=True)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@router.post("/sessions")
async def start_spelling_session(word_list_id: str, user=Depends(get_current_user)):
    """Start a new spelling session"""
    from uuid import uuid4
    session_id = f"sp_{uuid4().hex}"
    
    q = """
    INSERT INTO spelling_sessions (id, user_id, word_list_id, started_at, status)
    VALUES (%s, %s, %s, UTC_TIMESTAMP(), 'active')
    """
    await execute_query(q, (session_id, user['userId'], word_list_id))
    
    return {"id": session_id, "status": "active"}

@router.post("/sessions/{session_id}/results")
async def record_spelling_result(session_id: str, word_id: str, is_correct: bool, user=Depends(get_current_user)):
    """Record spelling result"""
    q = """
    INSERT INTO spelling_results (id, session_id, word_id, is_correct, created_at)
    VALUES (UUID(), %s, %s, %s, UTC_TIMESTAMP())
    """
    await execute_query(q, (session_id, word_id, int(is_correct)))
    
    return {"ok": True}

@router.get("/stats/me")
async def get_spelling_stats(user=Depends(get_current_user)):
    """Get user spelling statistics"""
    q = """
    SELECT COUNT(*) as total_sessions,
           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions
    FROM spelling_sessions
    WHERE user_id = %s
    """
    stats = await execute_query(q, (user['userId'],), fetchone=True)
    return stats or {"total_sessions": 0, "completed_sessions": 0}
