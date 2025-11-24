# src/ai/__init__.py
"""AI helpers for TULKKA: transcription, processing, generation and orchestration.

This module exposes the main AI entrypoints and generator types. The underlying
generator implementations have been upgraded to production-quality versions
in :mod:`src.ai.generators`, but the public surface here stays small and clean.
"""

from .transcription import transcribe_recording, TranscriptionError
from .processors import clean_transcript_text, split_into_paragraphs, extract_keywords
from .generators import (
    Flashcard,
    ClozeItem,
    GrammarQuestion,
    SentenceItem,
    generate_flashcards,
    generate_cloze,
    generate_grammar,
    generate_sentence_items,
)
from .orchestrator import process_transcript_to_exercises

__all__ = [
    "transcribe_recording",
    "TranscriptionError",
    "clean_transcript_text",
    "split_into_paragraphs",
    "extract_keywords",
    "Flashcard",
    "ClozeItem",
    "GrammarQuestion",
    "SentenceItem",
    "generate_flashcards",
    "generate_cloze",
    "generate_grammar",
    "generate_sentence_items",
    "process_transcript_to_exercises",
]
