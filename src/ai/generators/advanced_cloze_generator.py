# src/ai/generators/advanced_cloze_generator.py
"""
Advanced cloze exercise generator.

Generates exercises with two blanks per sentence for more challenging practice.
Uses clean, pedagogically sound sentences - never transcript noise.
"""

from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any, Set
from .shared_utils import _build_options_for_target, _clean_sentence_for_example, _assess_difficulty

# Noise patterns to filter out
NOISE_WORDS: Set[str] = {"okay", "ok", "um", "uh", "hmm", "yeah", "right", "so", "well"}
NOISE_NAMES: Set[str] = {"khadija", "basmala", "emam", "mahaba", "philip", "pass"}

# Clean fallback sentences for advanced cloze (must have 6+ words)
FALLBACK_SENTENCES = [
    "I think you already know the answer.",
    "Can you open the window for me?",
    "She goes to school every morning.",
    "We had a great time at the party.",
    "Please write your name on the paper.",
    "I want to learn a new language.",
]


def _is_clean_for_cloze(sentence: str) -> bool:
    """Check if a sentence is suitable for advanced cloze exercises."""
    if not sentence:
        return False
    
    words = sentence.split()
    
    # Must have at least 6 words for two blanks
    if len(words) < 6:
        return False
    
    lower = sentence.lower()
    
    # Skip sentences with names
    if any(name in lower for name in NOISE_NAMES):
        return False
    
    # Skip sentences starting with filler words
    first_word = words[0].lower().rstrip(".,!?")
    if first_word in NOISE_WORDS:
        return False
    
    # Skip sentences with ellipsis
    if "..." in sentence or "…" in sentence:
        return False
    
    # Must end with proper punctuation
    if sentence.rstrip()[-1] not in ".!?":
        return False
    
    # Skip malformed sentences
    if re.search(r"[,;:]\s*[.!?]$", sentence):
        return False
    
    return True


def generate_advanced_cloze(sentences: List[Dict[str, Any]], *, limit: int = 2) -> List[Dict[str, Any]]:
    """
    Generate advanced cloze exercises with two blanks per sentence.
    
    Args:
        sentences: List of sentence dictionaries
        limit: Maximum number of exercises to generate
    
    Returns:
        List of advanced cloze exercise dictionaries.
    """
    out: List[Dict[str, Any]] = []
    cnt = 0
    used_sentences: Set[str] = set()
    
    # First pass: try to use provided sentences that are clean
    for s in (sentences or []):
        if cnt >= limit:
            break
        if isinstance(s, dict):
            sent = s.get("sentence") or s.get("text") or s.get("english_sentence") or ""
        else:
            sent = str(s)
        
        sent = _clean_sentence_for_example(sent)
        
        if not _is_clean_for_cloze(sent):
            continue
        
        if sent.lower() in used_sentences:
            continue
        
        words = re.findall(r"[A-Za-z']+", sent)
        
        # Filter names (mid-sentence capitalized words)
        if any(w[0].isupper() and i != 0 for i, w in enumerate(words)):
            continue
        
        # Need at least 2 content words (length > 3) for blanks
        candidates = [w for w in words[1:-1] if len(w) > 3]
        if len(candidates) < 2:
            continue
        
        w1 = candidates[0]
        w2 = candidates[min(2, len(candidates)-1)]
        
        if w1.lower() == w2.lower():
            continue
        
        used_sentences.add(sent.lower())
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
    
    # Second pass: fill with fallback sentences if needed
    for fallback in FALLBACK_SENTENCES:
        if cnt >= limit:
            break
        if fallback.lower() in used_sentences:
            continue
        
        words = re.findall(r"[A-Za-z']+", fallback)
        candidates = [w for w in words[1:-1] if len(w) > 3]
        
        if len(candidates) < 2:
            continue
        
        w1 = candidates[0]
        w2 = candidates[min(2, len(candidates)-1)]
        
        if w1.lower() == w2.lower():
            continue
        
        used_sentences.add(fallback.lower())
        cloze_sent = fallback.replace(w1, "_____", 1).replace(w2, "_____", 1)
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
            "difficulty": _assess_difficulty(fallback),
            "source_sentence": fallback,
            "concept": "advanced_cloze"
        })
        cnt += 1
    
    return out[:limit]
