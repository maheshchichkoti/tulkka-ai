# src/ai/__init__.py
"""AI helpers for TULKKA: transcription, processing, generation and orchestration."""
from .transcription import transcribe_recording, TranscriptionError
from .processors import clean_transcript_text, split_into_paragraphs, extract_keywords
from .generators import (
    Flashcard,
    ClozeItem,
    GrammarQuestion,
    SentenceItem,
    generate_flashcards_from_text,
    generate_cloze_from_text,
    generate_grammar_from_text,
    generate_sentence_items_from_text,
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
    "generate_flashcards_from_text",
    "generate_cloze_from_text",
    "generate_grammar_from_text",
    "generate_sentence_items_from_text",
    "process_transcript_to_exercises",
]
