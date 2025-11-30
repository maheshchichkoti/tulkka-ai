# src/ai/__init__.py
"""AI helpers for TULKKA: transcription, processing, generation and orchestration.

This module exposes the main AI entrypoints and generator types. The underlying
generator implementations have been upgraded to production-quality versions
in :mod:`src.ai.generators`, but the public surface here stays small and clean.

Game Types (32 items per lesson):
- Flashcards: 8 items
- Spelling Bee: 8 items
- Fill-in-the-Blank: 8 items
- Sentence Builder: 3 items
- Grammar Challenge: 3 items
- Advanced Cloze: 2 items
"""

from .transcription import transcribe_recording, TranscriptionError
from .processors import clean_transcript_text, split_into_paragraphs, extract_keywords
from .generators import (
    # Generator functions
    generate_flashcards,
    generate_spelling_items,
    generate_fill_blank,
    generate_sentence_builder,
    generate_grammar_challenge,
    generate_advanced_cloze,
    # Backward-compatible aliases
    generate_cloze,
    generate_grammar,
    generate_sentence_items,
)
from .orchestrator import process_transcript_to_exercises
from .lesson_processor import LessonProcessor

__all__ = [
    # Transcription
    "transcribe_recording",
    "TranscriptionError",
    # Text processing
    "clean_transcript_text",
    "split_into_paragraphs",
    "extract_keywords",
    # Generator functions
    "generate_flashcards",
    "generate_spelling_items",
    "generate_fill_blank",
    "generate_sentence_builder",
    "generate_grammar_challenge",
    "generate_advanced_cloze",
    # Backward-compatible aliases
    "generate_cloze",
    "generate_grammar",
    "generate_sentence_items",
    # Orchestration
    "process_transcript_to_exercises",
    "LessonProcessor",
]
