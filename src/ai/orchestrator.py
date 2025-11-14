# src/ai/orchestrator.py
"""
High-level orchestrator that takes a transcript (or a Supabase zoom_summaries row),
processes it, generates exercises, and stores them into Supabase.lesson_exercises.

This module is the integration point used by your worker `zoom_processor.py`.
It keeps side effects isolated and returns a summary payload for logging/testing.
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

def _build_exercises_payload(
    source_row: Dict[str, Any],
    flashcards,
    cloze_items,
    grammar_questions,
    sentence_items
) -> Dict[str, Any]:
    """
    Build a consistent supabase lesson_exercises payload:
    - lesson_id, meeting_id, created_at, exercises: { flashcards: [...], cloze: [...], ... }
    """
    payload = {
        "lesson_id": source_row.get("meeting_id") or source_row.get("id"),
        "meeting_id": source_row.get("meeting_id") or source_row.get("id"),
        "teacher_email": source_row.get("teacher_email"),
        "source_row_id": source_row.get("id"),
        "generated_at": utc_now_iso(),
        "exercises": {
            "flashcards": [fc.__dict__ for fc in flashcards],
            "cloze": [ci.__dict__ for ci in cloze_items],
            "grammar": [gq.__dict__ for gq in grammar_questions],
            "sentence": [si.__dict__ for si in sentence_items],
        },
        "metadata": {
            "transcript_length": len(source_row.get("transcript","") or ""),
        },
        "status": "pending_approval"
    }
    return payload

def process_transcript_to_exercises(
    summary_row: Dict[str, Any],
    *,
    assemblyai_api_key: Optional[str] = None,
    transcribe_fn: Optional[callable] = None,
    llm_fn: Optional[callable] = None,
    limits: Optional[Dict[str,int]] = None,
    persist: bool = True
) -> Dict[str, Any]:
    """
    Full pipeline:
      1) Transcribe (or read transcript)
      2) Clean & split
      3) Extract keywords (for metadata)
      4) Generate exercises (flashcards, cloze, grammar, sentence)
      5) Persist to Supabase.lesson_exercises (if persist=True)
      6) Return a summary dict
    Parameters:
      - summary_row: supabase zoom_summaries row (dict)
      - assemblyai_api_key/transcribe_fn: provide either for audio transcription
      - llm_fn: optional callable(paragraph, task) to produce better output
      - limits: dict overrides like {"flashcards":20, "cloze":10, ...}
    """
    limits = limits or {}
    flash_limit = int(limits.get("flashcards", 20))
    cloze_limit = int(limits.get("cloze", 10))
    grammar_limit = int(limits.get("grammar", 10))
    sentence_limit = int(limits.get("sentence", 10))

    # Step 1: transcribe if transcript missing
    transcript_text = summary_row.get("transcript")
    transcription_source = summary_row.get("transcript_source")
    try:
        if not transcript_text:
            t = transcribe_recording(summary_row, assemblyai_api_key=assemblyai_api_key, transcribe_fn=transcribe_fn)
            transcript_text = t.get("text", "")
            transcription_source = t.get("source")
    except TranscriptionError as exc:
        logger.exception("Transcription failed: %s", exc)
        # Let caller handle marking row as failed; return summary
        return {"ok": False, "reason": "transcription_failed", "error": str(exc)}

    # Step 2-4: Process with LessonProcessor
    try:
        lesson_number = summary_row.get("lesson_number", 1)
        result = lesson_processor.process_lesson(transcript_text, lesson_number)
        
        flashcards = result.get('flashcards', [])
        cloze_items = result.get('cloze', [])
        grammar_questions = result.get('grammar', [])
        sentence_items = result.get('sentence', [])
        keywords = []  # Could extract from metadata
    except Exception as e:
        logger.exception("Generation step failed: %s", e)
        return {"ok": False, "reason": "generation_failed", "error": str(e)}

    payload = _build_exercises_payload(summary_row, flashcards, cloze_items, grammar_questions, sentence_items)

    # Persist to supabase.lesson_exercises
    if persist:
        try:
            inserted = supabase.insert_lesson_exercises(payload)
            logger.info("Inserted lesson_exercises id=%s for summary=%s", inserted.get("id") if inserted else None, summary_row.get("id"))
            return {"ok": True, "inserted": inserted, "counts": {"flashcards": len(flashcards), "cloze": len(cloze_items), "grammar": len(grammar_questions), "sentence": len(sentence_items)}, "keywords": keywords}
        except Exception:
            logger.exception("Failed to insert lesson_exercises into supabase")
            return {"ok": False, "reason": "persist_failed"}
    else:
        # return payload without persisting for testing
        return {"ok": True, "payload": payload, "counts": {"flashcards": len(flashcards), "cloze": len(cloze_items), "grammar": len(grammar_questions), "sentence": len(sentence_items)}, "keywords": keywords}
