# src/games/services/wordlists_service.py
from typing import Any, Dict, List, Optional
from src.games.dao import wordlists_dao, words_dao

def create_word_list(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    name = payload.get('name')
    description = payload.get('description')
    class_id = payload.get('classId') or payload.get('class_id')
    return wordlists_dao.create_word_list(user_id, name, description, class_id)

def list_word_lists(user_id: str, class_id: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    return wordlists_dao.list_word_lists(user_id, class_id, limit, offset)

def get_word_list(user_id: str, list_id: str, include_words: bool = False, page: int = 1, limit: int = 100) -> Dict[str, Any]:
    wl = wordlists_dao.get_word_list(list_id, user_id)
    if not wl:
        return None
    if include_words:
        offset = (page - 1) * limit
        wl['words'] = words_dao.list_words_for_list(list_id, limit, offset)
    return wl

def update_word_list(user_id: str, list_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return wordlists_dao.update_word_list(list_id, user_id, patch)

def delete_word_list(user_id: str, list_id: str) -> bool:
    return wordlists_dao.delete_word_list(list_id, user_id)
