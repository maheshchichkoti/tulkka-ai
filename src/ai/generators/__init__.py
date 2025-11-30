# src/ai/generators/__init__.py
"""
Exercise generators for Tulkka AI.

This module provides rule-based generators for creating various types of
language learning exercises from extracted vocabulary, mistakes, and sentences.

Game Types (32 items per lesson):
- Flashcards: 8 items
- Spelling Bee: 8 items  
- Fill-in-the-Blank: 8 items
- Sentence Builder: 3 items
- Grammar Challenge: 3 items
- Advanced Cloze: 2 items
"""

from typing import List, Dict, Any

from .flashcards_generator import generate_flashcards
from .spelling_generator import generate_spelling_items
from .fill_blank_generator import generate_fill_blank
from .sentence_builder_generator import generate_sentence_builder
from .grammar_generator import generate_grammar_challenge
from .advanced_cloze_generator import generate_advanced_cloze
from .shared_utils import _translator, _tr, _assess_difficulty

__all__ = [
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
]


# Backward-compatible aliases (older code may call these)
def generate_cloze(
    mistakes: List[Dict[str, Any]],
    transcript: str,
    *,
    limit: int = 8
) -> List[Dict[str, Any]]:
    """Alias for generate_fill_blank (backward compatibility)."""
    return generate_fill_blank(mistakes, transcript, limit=limit)


def generate_grammar(
    mistakes: List[Dict[str, Any]],
    *,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """Alias for generate_grammar_challenge (backward compatibility)."""
    return generate_grammar_challenge(mistakes, limit=limit)


def generate_sentence_items(
    sentences: List[Dict[str, Any]],
    *,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """Alias for generate_sentence_builder (backward compatibility)."""
    return generate_sentence_builder(sentences, limit=limit)
