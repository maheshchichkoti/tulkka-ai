# src/games/services/wordlists_service.py
from typing import Any, Dict, List, Optional
from src.games.dao import wordlists_dao, words_dao

async def create_word_list(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    name = payload.get('name')
    description = payload.get('description')
    class_id = payload.get('classId') or payload.get('class_id')
    return await wordlists_dao.create_wordlist(user_id, name, description)

async def list_word_lists(user_id: str, class_id: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    page = (offset // limit) + 1
    return await wordlists_dao.get_wordlists(user_id, search="", favorite=None, page=page, limit=limit)

async def get_word_list(user_id: str, list_id: str, include_words: bool = False, page: int = 1, limit: int = 100) -> Dict[str, Any]:
    wl = await wordlists_dao.get_wordlist_by_id(list_id, user_id)
    if not wl:
        return None
    if include_words:
        offset = (page - 1) * limit
        wl['words'] = await words_dao.get_words_by_list(list_id, limit, offset)
    return wl

async def update_word_list(user_id: str, list_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return await wordlists_dao.update_wordlist(list_id, user_id, patch)

async def delete_word_list(user_id: str, list_id: str) -> bool:
    return await wordlists_dao.delete_wordlist(list_id, user_id)
