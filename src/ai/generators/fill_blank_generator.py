# src/ai/generators/fill_blank_generator.py
from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any
from .shared_utils import _build_options_for_target, _assess_difficulty, _clean_sentence_for_example
# Note: we intentionally do NOT import any example-sentence picker here;
# this module defines its own _pick_example_in_text helper below.

NOISE_WORDS = {"emam", "basmala", "khadija", "mahaba", "pass"}

def _strip_speaker_labels(text: str) -> str:
    """Remove speaker labels like 'basmala emam:' or 'Khadija:'."""
    return re.sub(r"[A-Za-z][A-Za-z ]{0,40}:\s*", "", text)

def _pick_example_in_text(word: str, transcript: str) -> str:
    if not transcript:
        return ""
    cleaned = _strip_speaker_labels(transcript)
    parts = re.split(r'(?<=[.!?])\s+', cleaned)
    word_l = word.lower()
    candidates = [p.strip() for p in parts if word_l in p.lower()]
    # Filter out sentences containing noise words
    candidates = [c for c in candidates if not any(n in c.lower() for n in NOISE_WORDS)]
    if not candidates:
        for p in parts:
            t = p.strip()
            if len(t.split()) >= 3 and not any(n in t.lower() for n in NOISE_WORDS):
                return _clean_sentence_for_example(t)
        return ""
    candidates.sort(key=lambda x: (len(x.split()), len(x)))
    s = candidates[0].strip()
    return _clean_sentence_for_example(s)

def generate_fill_blank(mistakes: List[Dict[str, Any]], transcript: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    out = []
    cnt = 0
    for m in (mistakes or []):
        if cnt >= limit:
            break
        correct = m.get("correct") or m.get("corrected") or m.get("fix") or m.get("suggestion") or ""
        raw = m.get("incorrect") or m.get("raw") or ""
        context = m.get("context") or ""
        if not correct and not raw:
            continue
        target = (correct or "").strip() or (raw.split()[0] if raw else "").strip()
        if not target:
            continue
        # Skip targets that contain non-letters or look like proper names (start with capital)
        if not re.match(r"^[a-zA-Z]+$", target):
            continue
        if target[0].isupper():
            # Heuristic: likely a proper name – skip
            continue
        if target.lower() in NOISE_WORDS:
            continue
        sentence_source = context or _pick_example_in_text(target, transcript) or raw or ""
        if any(n in sentence_source.lower() for n in NOISE_WORDS):
            continue
        if target in sentence_source:
            sentence = sentence_source.replace(target, "_____")
        else:
            sentence = "_____ " + sentence_source
        typ = (m.get("type") or "").lower()
        if "verb" in typ:
            concept_hint = "third_person"
            concept = "verb_tense"
        elif "article" in typ:
            concept_hint = "article"
            concept = "article"
        elif "preposition" in typ:
            concept_hint = "preposition"
            concept = "preposition"
        elif "plural" in typ:
            concept_hint = "plural"
            concept = "plural"
        else:
            concept_hint = None
            concept = "general"
        options = _build_options_for_target(target, concept_hint)
        explanation = m.get("rule") or f"Correct form: {target}."
        hint = "Choose the grammatically correct option."
        difficulty = _assess_difficulty(target if target else sentence)
        out.append({
            "id": str(uuid.uuid4()),
            "sentence": sentence,
            "options": options,
            "correct_answer": target,
            "difficulty": difficulty,
            "source_mistake": raw or context,
            "explanation": explanation,
            "hint": hint,
            "concept": concept
        })
        cnt += 1

    # If we still have room, generate clozes from clean transcript sentences.
    if cnt < limit and transcript:
        parts = re.split(r'(?<=[.!?])\s+', transcript)
        for p in parts:
            if cnt >= limit:
                break
            s = _clean_sentence_for_example(p.strip())
            if not s:
                continue
            tokens = re.findall(r"[A-Za-z']+", s)
            if len(tokens) < 5:
                continue
            # pick a middle content word (length>3, lowercase)
            whitelist = {"open", "camera", "please", "name", "fine", "great", "amazing", "think", "already", "letters", "morning", "start", "close", "know"}
            content_words = [w for w in tokens[1:-1] if w in whitelist]
            if not content_words:
                continue
            target = content_words[len(content_words)//2]
            options = _build_options_for_target(target)
            cloze_sent = s.replace(target, "_____", 1)
            out.append({
                "id": str(uuid.uuid4()),
                "sentence": cloze_sent,
                "options": options,
                "correct_answer": target,
                "difficulty": _assess_difficulty(target),
                "source_mistake": "auto_sentence",
                "explanation": f"Correct: {target}",
                "hint": "Choose the word that best fits the sentence.",
                "concept": "vocab_cloze"
            })
            cnt += 1

    return out[:limit]
