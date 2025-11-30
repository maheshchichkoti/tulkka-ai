# src/ai/generators/advanced_cloze_generator.py
from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any
from .shared_utils import _build_options_for_target, _clean_sentence_for_example, _assess_difficulty

def generate_advanced_cloze(sentences: List[Dict[str, Any]], *, limit: int = 2) -> List[Dict[str, Any]]:
    out = []
    cnt = 0
    for s in (sentences or []):
        if cnt >= limit:
            break
        if isinstance(s, dict):
            sent = s.get("sentence") or s.get("text") or s.get("english_sentence") or ""
        else:
            sent = str(s)
        sent = _clean_sentence_for_example(sent)
        if re.search(r"[,;:]\s*[.!?]$", sent):
            continue
        words = re.findall(r"[A-Za-z']+", sent)
        if len(words) < 6:
            continue
        # filter names
        if any(w[0].isupper() and i != 0 for i, w in enumerate(words)):
            continue
        candidates = [w for w in words[1:-1] if len(w) > 3]
        if len(candidates) < 2:
            continue
        w1 = candidates[0]
        w2 = candidates[min(2, len(candidates)-1)]
        if w1.lower() == w2.lower():
            continue
        cloze_sent = sent.replace(w1, "_____", 1).replace(w2, "_____", 1)
        options1 = _build_options_for_target(w1)
        options2 = _build_options_for_target(w2)
        out.append({
            "id": str(uuid.uuid4()),
            "sentence": cloze_sent,
            "blank1": {
                "options": options1,
                "correct": w1,
                "hint": "Consider the grammar and meaning of blank 1."
            },
            "blank2": {
                "options": options2,
                "correct": w2,
                "hint": "Consider the grammar and meaning of blank 2."
            },
            "difficulty": _assess_difficulty(sent),
            "source_sentence": sent,
            "concept": "advanced_cloze"
        })
        cnt += 1
    return out[:limit]
