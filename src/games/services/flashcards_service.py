from typing import List
from uuid import uuid4
from datetime import datetime
from src.api.errors import APIError
from src.games.services import wordlists_service
from src.games.dao.flashcards_dao import FlashcardsDAO

class FlashcardsService:

    def __init__(self):
        self.dao = FlashcardsDAO()

    async def start_session(self, user_id: str, body):
        wl = await wordlists_service.get_word_list(user_id, body.wordListId)
        if wl is None:
            raise APIError("unknown_list", "Word list not found", 404)

        if body.selectedWordIds:
            words = await self.dao.fetch_subset_words(body.wordListId, body.selectedWordIds)
        else:
            words = await self.dao.fetch_list_words(body.wordListId)

        if not words:
            raise APIError("validation_error", "No words available", 400)

        session_id = f"fs_{uuid4().hex}"
        await self.dao.create_session(session_id, user_id, body.wordListId, len(words))

        for w in words:
            w["accuracy"] = int(100 * w["correct_count"] / max(1, w["practice_count"]))

        return {
            "id": session_id,
            "wordListId": body.wordListId,
            "words": words,
            "progress": {"current": 0, "total": len(words), "correct": 0, "incorrect": 0},
            "startedAt": datetime.utcnow().isoformat() + "Z",
            "completedAt": None,
        }

    async def record_result(self, user_id: str, session_id: str, body):
        session = await self.dao.get_session(session_id)
        if not session:
            raise APIError("not_found", "Session not found", 404)
        if session["user_id"] != user_id:
            raise APIError("forbidden", "Not owner", 403)

        wl_id = session["list_id"]
        wl = await wordlists_service.get_word_list(user_id, wl_id)
        if not wl:
            raise APIError("unknown_list", "List not found", 404)

        wl_words = await self.dao.fetch_list_words(wl_id)
        wl_ids = {w["id"] for w in wl_words}
        if body.wordId not in wl_ids:
            raise APIError("not_in_list", "Word not in list", 400)

        await self.dao.insert_result(session_id, body.wordId, body.isCorrect, body.attempts, body.timeSpent)
        await self.dao.update_word_stats(body.wordId, body.isCorrect)
        await self.dao.update_session_progress(session_id, body.isCorrect)

        return {"ok": True}

    async def complete_session(self, user_id: str, session_id: str, body):
        session = await self.dao.get_session(session_id)
        if not session:
            raise APIError("not_found", "Session not found", 404)
        if session["user_id"] != user_id:
            raise APIError("forbidden", "Not owner", 403)

        await self.dao.complete_session(session_id, body.progress.dict() if body.progress else None)

        session = await self.dao.get_session(session_id)

        return {
            "id": session["id"],
            "wordListId": session["list_id"],
            "words": [],
            "progress": {
                "current": session["progress_current"],
                "total": session["progress_total"],
                "correct": session["correct"],
                "incorrect": session["incorrect"],
            },
            "startedAt": session["started_at"].isoformat() + "Z",
            "completedAt": session["completed_at"].isoformat() + "Z",
        }
