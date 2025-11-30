"""High-quality flashcard generator (rule-based).

For each vocab item we ensure:
- Correct Hebrew translations for tricky words via overrides
- A clean example sentence (from extractor or transcript fallback)
"""

from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any
from .shared_utils import _translator, _tr, _assess_difficulty, _clean_sentence_for_example


TRANSLATION_OVERRIDES = {
    # Sense-correct overrides for common polysemous words
    "fine": "בסדר",   # "I'm fine" → בסדר
    "great": "מצוין",  # "great/excellent" → מצוין
}


def _pick_example_in_text(word: str, transcript: str) -> str:
    """Pick a short, clean sentence from transcript that contains the word.

    Falls back to the first reasonable sentence if none contain the word.
    """
    if not transcript or not word:
        return ""

    # Strip speaker labels (e.g., "Khadija:" or "basmala emam:")
    cleaned = re.sub(r"[A-Za-z][A-Za-z ]{0,40}:\s*", "", transcript)

    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    word_l = word.lower()
    candidates = [p.strip() for p in parts if word_l in p.lower()]

    if not candidates:
        for p in parts:
            t = p.strip()
            if len(t.split()) >= 3:
                return _clean_sentence_for_example(t)
        return ""

    candidates.sort(key=lambda x: (len(x.split()), len(x)))
    return _clean_sentence_for_example(candidates[0])


def generate_flashcards(vocab: List[Dict[str, Any]], transcript: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    t = _translator("he")
    out: List[Dict[str, Any]] = []
    cnt = 0

    for v in (vocab or []):
        if cnt >= limit:
            break

        if isinstance(v, dict):
            word = (v.get("word") or v.get("text") or "").strip()
            example = v.get("example_sentence") or v.get("context") or ""
            source = v.get("category") or "vocabulary_extractor"
        else:
            word = str(v).strip()
            example = ""
            source = "vocabulary_extractor"

        if not word:
            continue

        # Always try to attach a meaningful example sentence
        if example:
            example_clean = _clean_sentence_for_example(example)
        else:
            example_clean = _pick_example_in_text(word, transcript)

        # Sense-correct translation with overrides, then translator fallback
        translation = TRANSLATION_OVERRIDES.get(word.lower()) or _tr(word, t)
        difficulty = _assess_difficulty(word)
        hint = f"Word from lesson ({source})"

        out.append({
            "id": str(uuid.uuid4()),
            "word": word,
            "translation": translation,
            "example_sentence": example_clean,
            "difficulty": difficulty,
            "source": source,
            "hint": hint,
        })
        cnt += 1

    return out
