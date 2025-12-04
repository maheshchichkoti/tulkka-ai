# src/ai/generators/grammar_generator.py
from __future__ import annotations
import uuid
import random
import re
from typing import List, Dict, Any
from .shared_utils import (
    _build_options_for_target,
    _assess_difficulty,
    _clean_sentence_for_example,
)

random.seed(1337)


def generate_grammar_challenge(
    mistakes: List[Dict[str, Any]], *, limit: int = 3
) -> List[Dict[str, Any]]:
    out = []
    cnt = 0
    for m in mistakes or []:
        if cnt >= limit:
            break
        correct = m.get("correct") or m.get("corrected") or m.get("fix") or ""
        raw = m.get("incorrect") or m.get("raw") or ""
        context = m.get("context") or ""

        # Skip if no valid correction
        if not correct or len(correct.strip()) < 2:
            continue

        # Get target token (must be a real word)
        target_token = correct.split()[0].strip()
        if len(target_token) < 2 or not re.match(r"^[A-Za-z]+$", target_token):
            continue

        # Build prompt - must have proper context
        prompt_sentence = context if context and len(context) > 10 else ""

        # Skip if no good context (don't generate broken prompts like "_____ _____.")
        if not prompt_sentence or len(prompt_sentence) < 10:
            continue

        # Ensure target is in the prompt
        if target_token.lower() not in prompt_sentence.lower():
            continue

        # Replace target with blank
        prompt_with_blank = re.sub(
            re.escape(target_token),
            "_____",
            prompt_sentence,
            count=1,
            flags=re.IGNORECASE,
        )

        # Validate the prompt is not broken
        if prompt_with_blank.count("_____") != 1:
            continue
        if prompt_with_blank.strip() in (
            "_____",
            "_____.",
            "_____ _____.",
            "_____ _____.",
        ):
            continue

        typ = (m.get("type") or "").lower()
        if "verb" in typ:
            concept = "verb_tense"
            hint_concept = (
                "third_person" if target_token.endswith("s") else "verb_forms"
            )
        elif "article" in typ:
            concept = "article"
            hint_concept = "article"
        elif "preposition" in typ:
            concept = "preposition"
            hint_concept = "preposition"
        else:
            concept = "grammar_general"
            hint_concept = None

        options = _build_options_for_target(target_token, hint_concept)
        explanation = m.get("rule") or f"Correct form: {target_token}."
        difficulty = _assess_difficulty(target_token)

        out.append(
            {
                "id": str(uuid.uuid4()),
                "prompt": _clean_sentence_for_example(prompt_with_blank),
                "options": options,
                "correct_answer": target_token,
                "explanation": explanation,
                "hint": "Choose the correct grammar form.",
                "difficulty": difficulty,
                "concept": concept,
                "source_mistake": raw or context,
            }
        )
        cnt += 1

    if cnt < limit:
        templates = [
            ("She ____ to school every day.", "goes", "third_person"),
            ("They ____ the book every week.", "read", "verb_forms"),
            ("I ____ an apple for breakfast.", "eat", "verb_forms"),
            ("He ____ a doctor.", "is", "be_verb"),
        ]
        for prompt, target_token, hint_concept in templates:
            if cnt >= limit:
                break
            options = _build_options_for_target(target_token, hint_concept)
            explanation = f"Correct form is '{target_token}'."
            out.append(
                {
                    "id": str(uuid.uuid4()),
                    "prompt": prompt,
                    "options": options,
                    "correct_answer": target_token,
                    "explanation": explanation,
                    "hint": "Select the correct word for the sentence.",
                    "difficulty": _assess_difficulty(target_token),
                    "concept": hint_concept,
                    "source_mistake": "auto_template",
                }
            )
            cnt += 1

    return out[:limit]
