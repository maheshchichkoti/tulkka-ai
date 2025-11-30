"""
FINAL PRODUCTION ORCHESTRATOR FOR TULKKA
Fully aligned with:
- New LessonProcessor output
- New generators (flashcards / spelling / fill_blank / sentence_builder / grammar_challenge / advanced_cloze)
- UI required counts
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional, List
from ..db.supabase_client import SupabaseClient
from .transcription import transcribe_recording, TranscriptionError
from .lesson_processor import LessonProcessor
from ..time_utils import utc_now_iso

logger = logging.getLogger(__name__)
supabase = SupabaseClient()
lesson_processor = LessonProcessor()


def _normalize(items):
    """Convert dataclasses / objects into dicts safely."""
    out = []
    for item in items or []:
        if isinstance(item, dict):
            out.append(item)
        elif hasattr(item, "to_dict"):
            try:
                out.append(item.to_dict())
            except:
                pass
        elif hasattr(item, "__dict__"):
            out.append(dict(item.__dict__))
    return out


def _build_payload(
    row,
    flashcards,
    spelling,
    fill_blank,
    sentence_builder,
    grammar_challenge,
    advanced_cloze
):
    exercises = {
        "flashcards": flashcards,
        "spelling": spelling,
        "fill_blank": fill_blank,
        "sentence_builder": sentence_builder,
        "grammar_challenge": grammar_challenge,
        "advanced_cloze": advanced_cloze,
        "counts": {
            "flashcards": len(flashcards),
            "spelling": len(spelling),
            "fill_blank": len(fill_blank),
            "sentence_builder": len(sentence_builder),
            "grammar_challenge": len(grammar_challenge),
            "advanced_cloze": len(advanced_cloze),
        },
        "transcript_length": len(row.get("transcript", "") or "")
    }

    return {
        "zoom_summary_id": row.get("id"),
        "user_id": row.get("user_id"),
        "teacher_id": row.get("teacher_id"),
        "class_id": row.get("class_id"),
        "generated_at": utc_now_iso(),
        "exercises": exercises,
        "status": "pending_approval",
    }


def process_transcript_to_exercises(
    summary_row: Dict[str, Any],
    *,
    assemblyai_api_key=None,
    transcribe_fn=None,
    llm_fn=None,
    limits=None,
    persist=True
):

    # -------------------------------
    # FIXED LIMITS (UI Aligned)
    # 8 + 8 + 8 + 3 + 3 + 2 = 32 items per lesson
    # -------------------------------
    flash_limit = 8           # Flashcards: 8 per session
    spelling_limit = 8        # Spelling Bee: 8 per session
    fill_blank_limit = 8      # Fill-in-the-Blank: 8 per session

    sentence_builder_limit = 3   # Sentence Builder: 1 per session (generate 3)
    grammar_challenge_limit = 3  # Grammar Challenge: 1 per session (generate 3)
    advanced_cloze_limit = 2     # Advanced Cloze: 2 per session

    # -------------------------------
    # 1. TRANSCRIPTION
    # -------------------------------
    transcript_text = summary_row.get("transcript")
    try:
        if not transcript_text:
            t = transcribe_recording(
                summary_row,
                assemblyai_api_key=assemblyai_api_key,
                transcribe_fn=transcribe_fn
            )
            transcript_text = t.get("text", "")
    except TranscriptionError as exc:
        logger.exception("Transcription failed")
        return {"ok": False, "reason": "transcription_failed", "error": str(exc)}

    # -------------------------------
    # 2. LESSON PROCESSING
    # -------------------------------
    try:
        result = lesson_processor.process_lesson(transcript_text)

        flashcards = _normalize(result.get("flashcards", []))[:flash_limit]
        spelling = _normalize(result.get("spelling", []))[:spelling_limit]
        fill_blank = _normalize(result.get("fill_blank", []))[:fill_blank_limit]

        sentence_builder = _normalize(result.get("sentence_builder", []))[:sentence_builder_limit]
        grammar_challenge = _normalize(result.get("grammar_challenge", []))[:grammar_challenge_limit]
        advanced_cloze = _normalize(result.get("advanced_cloze", []))[:advanced_cloze_limit]

    except Exception as e:
        logger.exception("Lesson processing failed")
        return {"ok": False, "reason": "generation_failed", "error": str(e)}

    # -------------------------------
    # 3. BUILD PAYLOAD
    # -------------------------------
    payload = _build_payload(
        summary_row,
        flashcards,
        spelling,
        fill_blank,
        sentence_builder,
        grammar_challenge,
        advanced_cloze
    )

    # -------------------------------
    # 4. SAVE TO SUPABASE
    # -------------------------------
    if persist:
        try:
            inserted = supabase.insert_lesson_exercises(payload)
            return {
                "ok": True,
                "inserted": inserted,
                "counts": payload["exercises"]["counts"]
            }
        except Exception:
            logger.exception("Persist failed")
            return {"ok": False, "reason": "persist_failed"}

    return {
        "ok": True,
        "payload": payload
    }
