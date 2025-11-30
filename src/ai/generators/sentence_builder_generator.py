# src/ai/generators/sentence_builder_generator.py
from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any
from .shared_utils import _translator, _tr, _clean_sentence_for_example, _assess_difficulty

def generate_sentence_builder(sentences: List[Dict[str, Any]], *, limit: int = 3) -> List[Dict[str, Any]]:
    t = _translator("he")
    out = []
    cnt = 0
    for s in (sentences or []):
        if cnt >= limit:
            break
        if isinstance(s, dict):
            sent = s.get("sentence") or s.get("text") or s.get("english_sentence") or ""
        else:
            sent = str(s)
        sent = sent.strip()
        if not sent:
            continue
        clean = _clean_sentence_for_example(sent)
        # Capitalise first letter if not already
        if clean and clean[0].islower():
            clean = clean[0].upper() + clean[1:]
        # If sentence is likely a question (starts with interrogative/auxiliary) and ends with a period → convert to '?'
        if clean.endswith(".") and re.match(r"^(can|could|what|why|how|where|when|do|does|did|is|are|am|will|would|shall|should|have|has|had)\b", clean, re.I):
            clean = clean[:-1] + "?"
        # Discard sentences that still look malformed (comma right before punctuation etc.)
        if re.search(r"[,;:]\s*[.!?]$", clean):
            continue
        words_only = re.findall(r"[A-Za-z']+", clean)
        if len(words_only) < 4:
            continue
        if any(w[0].isupper() and i != 0 for i, w in enumerate(words_only)):
            # skip sentences with mid-sentence capitalized words (likely names)
            continue
        tokens = re.findall(r"[A-Za-z']+|[,\.\.!?;:]", clean)
        accepted = [tokens]
        translation = _tr(clean, t) if t else ""
        hint = "Rebuild the sentence in the correct order."
        difficulty = _assess_difficulty(clean)
        out.append({
            "id": str(uuid.uuid4()),
            "english": clean,
            "tokens": tokens,
            "accepted": accepted,
            "translation": translation,
            "hint": hint,
            "difficulty": difficulty,
        })
        cnt += 1
    return out
