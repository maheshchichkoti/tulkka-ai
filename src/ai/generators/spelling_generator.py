"""Spelling generator (rule-based, production-ready).

Each item:
- uses the same translations as flashcards (including overrides)
- includes a helpful hint (Hebrew translation)
- always has a clean, pedagogically sound sample sentence
"""

from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any
from .shared_utils import _translator, _tr, _assess_difficulty, _clean_sentence_for_example

# Import clean example sentences from flashcards generator
from .flashcards_generator import (
    TRANSLATION_OVERRIDES,
    EXAMPLE_SENTENCES,
    NOISE_WORDS,
    NOISE_NAMES,
    _is_clean_sentence,
)


def _get_spelling_example(word: str, transcript: str) -> str:
    """Get a clean example sentence for spelling practice.
    
    Priority:
    1. Pre-defined clean example sentences
    2. Clean sentence from transcript (if passes quality check)
    3. Generated fallback sentence
    """
    word_lower = word.lower()
    
    # Priority 1: Use pre-defined clean examples
    if word_lower in EXAMPLE_SENTENCES:
        return EXAMPLE_SENTENCES[word_lower]
    
    # Priority 2: Try to find a clean sentence in transcript
    if transcript:
        cleaned = re.sub(r"[A-Za-z][A-Za-z ]{0,40}:\s*", "", transcript)
        parts = re.split(r"(?<=[.!?])\s+", cleaned)
        
        for p in parts:
            sentence = _clean_sentence_for_example(p.strip())
            if word_lower in sentence.lower() and _is_clean_sentence(sentence):
                return sentence
    
    # Priority 3: Generate a simple fallback
    return f"Can you spell the word '{word}'?"


def generate_spelling_items(vocab: List[Dict[str, Any]], transcript: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Generate spelling exercises from vocabulary list.
    
    Args:
        vocab: List of vocabulary items (dicts with 'word', 'text', etc.)
        transcript: Full transcript for context extraction
        limit: Maximum number of spelling items to generate
    
    Returns:
        List of spelling exercise dictionaries.
    """
    t = _translator("he")
    out: List[Dict[str, Any]] = []
    cnt = 0

    for v in (vocab or []):
        if cnt >= limit:
            break

        if isinstance(v, dict):
            word = (v.get("word") or v.get("text") or "").strip()
            source = v.get("category") or "content_word"
            provided_sentence = v.get("example_sentence") or v.get("context") or ""
        else:
            word = str(v).strip()
            source = "content_word"
            provided_sentence = ""

        if not word:
            continue

        # Translation with the same overrides as flashcards
        translation = TRANSLATION_OVERRIDES.get(word.lower()) or _tr(word, t)

        # Get a clean example sentence
        sample_sentence = _get_spelling_example(word, transcript)
        
        # If provided sentence is clean, prefer it
        if provided_sentence and _is_clean_sentence(provided_sentence):
            sample_sentence = _clean_sentence_for_example(provided_sentence)

        hint = translation or "Spell the word carefully."
        difficulty = _assess_difficulty(word)

        out.append({
            "id": str(uuid.uuid4()),
            "word": word,
            "translation": translation,
            "hint": hint,
            "difficulty": difficulty,
            "source": source,
            "sample_sentence": sample_sentence,
        })
        cnt += 1

    return out
