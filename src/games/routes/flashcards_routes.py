# src/games/routes/flashcards_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status, Header
from typing import Optional
from src.games.middlewares.auth import get_current_user
from src.games.middlewares.idempotency import check_idempotency, save_idempotent_response, IDEMPOTENCY_HEADER
from src.games.services import wordlists_service
from src.games.services.flashcards_service import FlashcardsService
from src.games.schemas.wordlists_schemas import WordListCreate, WordListUpdate
from src.games.schemas.words_schemas import WordCreate, WordUpdate
from src.games.schemas.flashcards_schemas import StartSessionRequest, PracticeResultRequest, CompleteSessionRequest

router = APIRouter(prefix="/v1", tags=["Games - Flashcards"])
flashcards_service = FlashcardsService()

# Word lists endpoints

@router.get("/word-lists")
async def list_word_lists(request: Request, page: int = 1, limit: int = 20, classId: Optional[str] = None, user=Depends(get_current_user)):
    data = await wordlists_service.list_word_lists(user['userId'], classId, limit=limit, offset=(page-1)*limit)
    return {"data": data, "pagination": {"page": page, "limit": limit, "total": len(data)}}

@router.post("/word-lists", status_code=201)
async def create_word_list(payload: WordListCreate, request: Request, user=Depends(get_current_user)):
    wl = await wordlists_service.create_word_list(user['userId'], payload.dict(by_alias=True))
    return wl

@router.get("/word-lists/{list_id}")
async def get_word_list(list_id: str, include: Optional[str] = Query(None), page: int = 1, limit: int = 100, user=Depends(get_current_user)):
    include_words = False
    if include and 'words' in include:
        include_words = True
    wl = await wordlists_service.get_word_list(user['userId'], list_id, include_words=include_words, page=page, limit=limit)
    if not wl:
        raise HTTPException(status_code=404, detail="Word list not found")
    return wl

@router.patch("/word-lists/{list_id}")
async def patch_word_list(list_id: str, payload: WordListUpdate, user=Depends(get_current_user)):
    wl = await wordlists_service.update_word_list(user['userId'], list_id, payload.dict(exclude_unset=True, by_alias=True))
    if not wl:
        raise HTTPException(status_code=404, detail="Word list not found or not allowed")
    return wl

@router.delete("/word-lists/{list_id}", status_code=204)
async def delete_word_list(list_id: str, user=Depends(get_current_user)):
    ok = await wordlists_service.delete_word_list(user['userId'], list_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found or not allowed")
    return {}

@router.post("/word-lists/{list_id}/favorite")
async def toggle_list_favorite(list_id: str, payload: dict, user=Depends(get_current_user)):
    """Toggle favorite status of a word list"""
    is_favorite = payload.get("isFavorite", True)
    wl = await wordlists_service.update_word_list(user['userId'], list_id, {"is_favorite": is_favorite})
    if not wl:
        raise HTTPException(status_code=404, detail="Word list not found")
    return {"ok": True, "isFavorite": is_favorite}

# Words routes (simple wrappers — service functions live in wordlists_service via DAOs)

@router.post("/word-lists/{list_id}/words", status_code=201)
async def add_word(list_id: str, payload: WordCreate, user=Depends(get_current_user)):
    from src.games.dao.words_dao import create_word
    w = await create_word(list_id, payload.word, payload.translation, payload.notes, payload.difficulty)
    return w

@router.patch("/word-lists/{list_id}/words/{word_id}")
async def update_word(list_id: str, word_id: str, payload: WordUpdate, user=Depends(get_current_user)):
    from src.games.dao.words_dao import update_word
    w = await update_word(word_id, list_id, payload.dict(exclude_unset=True, by_alias=True))
    if not w:
        raise HTTPException(status_code=404, detail="Word not found")
    return w

@router.delete("/word-lists/{list_id}/words/{word_id}", status_code=204)
async def remove_word(list_id: str, word_id: str, user=Depends(get_current_user)):
    from src.games.dao.words_dao import delete_word
    ok = await delete_word(word_id, list_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Word not found")
    return {}

@router.post("/word-lists/{list_id}/words/{word_id}/favorite")
async def toggle_word_favorite(list_id: str, word_id: str, payload: dict, user=Depends(get_current_user)):
    """Toggle favorite status of a word"""
    from src.games.dao.words_dao import update_word
    is_favorite = payload.get("isFavorite", True)
    w = await update_word(word_id, list_id, {"is_favorite": is_favorite})
    if not w:
        raise HTTPException(status_code=404, detail="Word not found")
    return {"ok": True, "isFavorite": is_favorite}

# Flashcard sessions

@router.post("/flashcards/sessions", status_code=201)
async def start_flashcards_session(payload: StartSessionRequest, request: Request, idempotency_key: Optional[str] = Header(None, alias=IDEMPOTENCY_HEADER), user=Depends(get_current_user)):
    # idempotency check
    prev = await check_idempotency(user['userId'], "/v1/flashcards/sessions", idempotency_key)
    if prev:
        return prev
    res = await flashcards_service.start_session(user['userId'], payload)
    if idempotency_key:
        await save_idempotent_response(user['userId'], "/v1/flashcards/sessions", idempotency_key, res)
    return res

@router.get("/flashcards/sessions/{session_id}")
async def get_flashcard_session(session_id: str, user=Depends(get_current_user)):
    session = await flashcards_service.dao.get_session(session_id)
    if not session or session["user_id"] != user['userId']:
        raise HTTPException(status_code=404, detail="Session not found")
    
    words = await flashcards_service.dao.fetch_list_words(session["list_id"])
    for w in words:
        w["accuracy"] = int(100 * w["correct_count"] / max(1, w["practice_count"]))
    
    return {
        "id": session["id"],
        "wordListId": session["list_id"],
        "words": words,
        "progress": {
            "current": session["progress_current"],
            "total": session["progress_total"],
            "correct": session["correct"],
            "incorrect": session["incorrect"]
        },
        "startedAt": session["started_at"].isoformat() + "Z",
        "completedAt": session["completed_at"].isoformat() + "Z" if session["completed_at"] else None
    }

@router.post("/flashcards/sessions/{session_id}/results")
async def record_flashcard_result(session_id: str, payload: PracticeResultRequest, request: Request, idempotency_key: Optional[str] = Header(None, alias=IDEMPOTENCY_HEADER), user=Depends(get_current_user)):
    route = f"/v1/flashcards/sessions/{session_id}/results"
    prev = await check_idempotency(user['userId'], route, idempotency_key)
    if prev:
        return prev
    res = await flashcards_service.record_result(user['userId'], session_id, payload)
    if idempotency_key:
        await save_idempotent_response(user['userId'], route, idempotency_key, res)
    return res

@router.post("/flashcards/sessions/{session_id}/complete")
async def complete_flashcard_session(session_id: str, payload: CompleteSessionRequest, user=Depends(get_current_user)):
    res = await flashcards_service.complete_session(user['userId'], session_id, payload)
    return res

@router.get("/flashcards/stats/me")
async def flashcard_stats(user=Depends(get_current_user)):
    # minimal aggregate: reuse existing progress endpoint if present
    from src.db.mysql_pool import execute_query
    q = """
        SELECT COUNT(*) as total_sessions,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
               AVG(final_score) as avg_score,
               SUM(correct_count) as total_correct,
               SUM(incorrect_count) as total_incorrect
        FROM game_sessions
        WHERE user_id = %s AND game_type = 'flashcards'
    """
    stats = await execute_query(q, (user['userId'],), fetchone=True)
    return {"totals": stats or {"total_sessions":0,"completed_sessions":0,"avg_score":0,"total_correct":0,"total_incorrect":0}}
