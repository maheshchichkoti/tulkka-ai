"""Spelling generator (rule-based, production-ready).

Each item:
- uses the same translations as flashcards (including overrides)
- includes a helpful hint (Hebrew translation)
- always has a sample sentence if we can find one in the transcript
"""

from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any
from .shared_utils import _translator, _tr, _assess_difficulty, _clean_sentence_for_example


TRANSLATION_OVERRIDES = {
    "fine": "בסדר",
    "great": "מצוין",
}


def _pick_example_in_text(word: str, transcript: str) -> str:
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


def generate_spelling_items(vocab: List[Dict[str, Any]], transcript: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    t = _translator("he")
    out: List[Dict[str, Any]] = []
    cnt = 0

    for v in (vocab or []):
        if cnt >= limit:
            break

        if isinstance(v, dict):
            word = (v.get("word") or v.get("text") or "").strip()
            source = v.get("category") or "vocabulary_extractor"
            sample_sentence = v.get("example_sentence") or v.get("context") or ""
        else:
            word = str(v).strip()
            source = "vocabulary_extractor"
            sample_sentence = ""

        if not word:
            continue

        # Translation with the same overrides as flashcards
        translation = TRANSLATION_OVERRIDES.get(word.lower()) or _tr(word, t)

        # Ensure we always have some example sentence if possible
        if not sample_sentence:
            sample_sentence = _pick_example_in_text(word, transcript)

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
