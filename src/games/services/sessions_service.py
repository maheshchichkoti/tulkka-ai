# src/games/services/sessions_service.py
from typing import List, Dict, Any, Optional
from src.games.dao import sessions_dao, words_dao
from src.games.dao import sessions_dao as sd

def start_flashcards_session(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    word_list_id = payload.get('wordListId') or payload.get('wordListId')
    selected_word_ids = payload.get('selectedWordIds')
    # load words if no selected ids
    if not selected_word_ids:
        selected = words_dao.list_words_for_list(word_list_id, limit=1000, offset=0)
        selected_word_ids = [w['id'] for w in selected]
    session = sd.start_session(user_id=user_id, game_type='flashcards', class_id=payload.get('classId') or None, item_ids=selected_word_ids, mode='list', reference_id=word_list_id)
    # produce response containing words meta
    words = []
    for w in selected_word_ids:
        rec = words_dao.get_word(w, word_list_id)
        if rec:
            words.append(rec)
    session['words'] = words
    return session

def get_session(user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    return sd.get_session(session_id, user_id)

def record_practice_result(user_id: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    rid = sd.record_result(session_id=session_id, game_type='flashcards', item_id=payload['itemId'], is_correct=payload['isCorrect'], attempts=payload.get('attempts',1), time_spent_ms=payload.get('timeSpentMs',0), metadata=payload.get('metadata'))
    # update word stats
    words_dao.increment_practice_stats(payload['itemId'], payload['isCorrect'])
    return {"id": rid, "ok": True}

def complete_session(user_id: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    final_score = payload.get('finalScore', 0.0)
    correct = payload.get('correctCount', 0)
    incorrect = payload.get('incorrectCount', 0)
    sd.complete_session(session_id, user_id, final_score, correct, incorrect)
    return {"id": session_id, "message": "Session completed"}
