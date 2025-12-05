"""
Three-call Groq-based pipeline helpers for lesson processing.

Provides:
 - GroqMistakeGrammarExtractor
 - GroqVocabSentenceExtractor
 - GroqClozeGenerator
 - run_three_call_pipeline(...) helper

Fully aligned with:
 - lesson_processor (flashcards, spelling, fill_blank, etc.)
 - UI expectations
 - generators.py structure
"""

from __future__ import annotations
import json
import logging
import os
import re
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# ---------------------------
# Groq Client Wrapper
# ---------------------------
try:
    from groq import Groq

    GROQ_AVAILABLE = True
except Exception as e:  # pragma: no cover - diagnostic logging
    # Log the actual import failure so we can debug configuration issues
    logger.exception("Failed to import groq Python client: %s", e)
    Groq = None  # type: ignore
    GROQ_AVAILABLE = False


class GroqClient:
    """Minimal safe wrapper for Groq chat completions."""

    def __init__(self, model: Optional[str] = None):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.enabled = bool(self.api_key and GROQ_AVAILABLE)
        self.client = None

        if not self.enabled:
            if not self.api_key:
                logger.info("GROQ_API_KEY not set; Groq disabled.")
            else:
                logger.info("groq package not installed; Groq disabled.")
            return

        try:
            self.client = Groq(api_key=self.api_key)
        except Exception as e:
            # Log the exception cleanly without causing a formatting error
            logger.exception("Groq init failed: %s", e)
            self.enabled = False
            self.client = None

    def chat(
        self, system_prompt, user_prompt, temperature=0.2, max_tokens=1200
    ) -> Optional[str]:
        if not self.enabled or not self.client:
            return None

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if not resp or not getattr(resp, "choices", None):
                return None

            choice = resp.choices[0]
            return getattr(
                getattr(choice, "message", None), "content", None
            ) or getattr(choice, "content", None)
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "rate limit" in msg.lower():
                logger.warning("Groq rate limit: %s", msg)
            else:
                logger.exception("Groq chat failure: %s", msg)
            return None


# ---------------------------
# JSON PARSING UTIL
# ---------------------------

_JSON_RE = re.compile(r"(\{.*\}|\[.*\])", flags=re.DOTALL)


def _parse_ai_json(text: str) -> Optional[Any]:
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    m = _JSON_RE.search(cleaned)
    payload = m.group(1) if m else cleaned

    try:
        return json.loads(payload)
    except Exception:
        # last chance: swap single → double quotes
        try:
            fixed = re.sub(r"(?<!\\)'", '"', payload)
            return json.loads(fixed)
        except Exception:
            logger.error("Failed to parse JSON from AI response")
            return None


# ---------------------------
# Transcript trimming
# ---------------------------


def trim_transcript(text: str, max_chars: int = 4000) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_chars:
        return t
    start = (len(t) // 2) - (max_chars // 2)
    return t[start : start + max_chars]


# ---------------------------
# Translation fallback helper
# ---------------------------


def _build_translator_fallback(target="he"):
    """Unified translator fallback."""
    # Try importing your generator translator:
    try:
        from ..generators import _translator

        return _translator(target)
    except Exception:
        pass

    # Deep-translator fallback
    try:
        from deep_translator import GoogleTranslator

        lang = "iw" if target == "he" else target
        return GoogleTranslator(source="en", target=lang)
    except Exception:
        return None


def _translate_word(word: str, translator) -> str:
    if not word or not translator:
        return ""
    try:
        return translator.translate(word)
    except Exception:
        return ""


# ---------------------------
# 1) Mistakes + Grammar
# ---------------------------


class GroqMistakeGrammarExtractor:
    """Groq call #1 — mistakes + grammar rules"""

    def __init__(self, groq=None):
        self.groq = groq or GroqClient()
        self.enabled = bool(self.groq and self.groq.enabled)
        self.translator = _build_translator_fallback("he")

    def extract(self, transcript: str, max_mistakes=12) -> Dict[str, Any]:
        if not transcript:
            return {"mistakes": [], "grammar_points": []}

        if not self.enabled:
            logger.info("Groq disabled → heuristic fallback.")
            from ..extractors import MistakeExtractor

            me = MistakeExtractor()
            mistakes = me.extract(transcript)
            grammar_points = [
                {
                    "rule": m.get("rule", ""),
                    "example": m.get("correct", ""),
                    "hebrew": "",
                }
                for m in mistakes
            ]
            return {
                "mistakes": mistakes[:max_mistakes],
                "grammar_points": grammar_points[:8],
            }

        # --- Groq prompt ---
        sys = "You are an expert ESL teacher. Extract mistakes and grammar points."
        trimmed = trim_transcript(transcript)

        user = f"""
Transcript:
{trimmed}

Instructions:
Return JSON with:
{{
  "mistakes": [
     {{
       "incorrect": "",
       "correct": "",
       "type": "",
       "rule": "",
       "context": ""
     }}
  ],
  "grammar_points": [
     {{
        "rule": "",
        "example": "",
        "hebrew": ""
     }}
  ]
}}
Max mistakes: {max_mistakes}
Max grammar_points: 8
No extra text.
"""

        text = self.groq.chat(sys, user, temperature=0.15, max_tokens=1000)
        parsed = _parse_ai_json(text)

        if not isinstance(parsed, dict):
            return {"mistakes": [], "grammar_points": []}

        # --- Normalize ---
        mistakes = []
        for m in parsed.get("mistakes", []) or []:
            inc = (m.get("incorrect") or "").strip()
            cor = (m.get("correct") or "").strip()
            typ = m.get("type") or "grammar_general"
            rule = m.get("rule") or ""
            ctx = m.get("context") or ""
            if inc and cor:
                mistakes.append(
                    {
                        "incorrect": inc,
                        "correct": cor,
                        "type": typ,
                        "rule": rule,
                        "context": ctx,
                    }
                )
            if len(mistakes) >= max_mistakes:
                break

        grammar_points = []
        for g in parsed.get("grammar_points", []) or []:
            rule = (g.get("rule") or "").strip()
            example = (g.get("example") or "").strip()
            heb = (g.get("hebrew") or "").strip()
            if not heb and self.translator:
                heb = _translate_word(rule, self.translator)
            grammar_points.append({"rule": rule, "example": example, "hebrew": heb})

        return {"mistakes": mistakes, "grammar_points": grammar_points}


# ---------------------------
# 2) Vocab + Sentences
# ---------------------------


class GroqVocabSentenceExtractor:
    """Groq call #2 — vocabulary + practice sentences"""

    def __init__(self, groq=None):
        self.groq = groq or GroqClient()
        self.enabled = bool(self.groq and self.groq.enabled)
        self.translator = _build_translator_fallback("he")

    def extract(self, transcript, max_vocab=15, max_sentences=12):
        if not transcript:
            return {"vocabulary": [], "sentences": []}

        if not self.enabled:
            logger.info("Groq disabled → heuristic vocab/sentence fallback.")
            from ..extractors import VocabularyExtractor, SentenceExtractor

            return {
                "vocabulary": VocabularyExtractor().extract(transcript),
                "sentences": SentenceExtractor().extract(transcript),
            }

        sys = "Extract 1–3 word vocabulary with Hebrew translation + good practice sentences."
        trimmed = trim_transcript(transcript)

        user = f"""
Transcript:
{trimmed}

Return STRICT JSON:
{{
  "vocabulary": [
     {{"word": "", "hebrew": "", "example": "", "difficulty": ""}}
  ],
  "sentences": [
     {{"sentence": "", "difficulty": "", "grammar_focus": ""}}
  ]
}}
Limits: {max_vocab} vocab, {max_sentences} sentences.
"""

        text = self.groq.chat(sys, user, temperature=0.2, max_tokens=1100)
        parsed = _parse_ai_json(text)

        if not isinstance(parsed, dict):
            return {"vocabulary": [], "sentences": []}

        vocab = []
        for v in parsed.get("vocabulary", []) or []:
            word = (v.get("word") or "").strip()
            heb = (v.get("hebrew") or "").strip()
            example = (v.get("example") or "").strip()
            diff = (v.get("difficulty") or "medium").strip()

            if not word:
                continue
            if not heb and self.translator:
                heb = _translate_word(word, self.translator)

            vocab.append(
                {"word": word, "hebrew": heb, "example": example, "difficulty": diff}
            )
            if len(vocab) >= max_vocab:
                break

        sentences = []
        for s in parsed.get("sentences", []) or []:
            sentence = (s.get("sentence") or "").strip()
            diff = (s.get("difficulty") or "medium").strip()
            gf = (s.get("grammar_focus") or "").strip()
            if sentence:
                sentences.append(
                    {"sentence": sentence, "difficulty": diff, "grammar_focus": gf}
                )
            if len(sentences) >= max_sentences:
                break

        return {"vocabulary": vocab, "sentences": sentences}


# ---------------------------
# 3) Cloze Generator
# ---------------------------


class GroqClozeGenerator:
    """Groq call #3 — fill-in-blank items"""

    def __init__(self, groq=None):
        self.groq = groq or GroqClient()
        self.enabled = bool(self.groq and self.groq.enabled)

    def generate(self, sentences, vocabulary, max_cloze=8):
        if not sentences:
            return []

        if not self.enabled:
            logger.info("Groq disabled → heuristic cloze fallback.")
            out = []
            for s in sentences[:max_cloze]:
                words = s["sentence"].split()
                target = words[len(words) // 2].strip(".,?!")
                blanked = s["sentence"].replace(target, "_____", 1)
                opts = [target, target + "s", target + "ed", target.upper()]
                out.append(
                    {
                        "sentence": blanked,
                        "correct_answer": target,
                        "options": opts[:4],
                        "difficulty": s.get("difficulty", "medium"),
                    }
                )
            return out

        vocab_list = [v["word"] for v in vocabulary][:20]
        sample = "\n".join(
            [f"{i+1}. {s['sentence']}" for i, s in enumerate(sentences[:20])]
        )

        sys = "You write clean ESL cloze questions."
        user = f"""
Sentences:
{sample}

Prefer blanks using:
{', '.join(vocab_list)}

Return STRICT JSON: list of objects:
[
  {{
    "sentence": "with exactly ONE _____",
    "answer": "correct word",
    "options": ["a","b","c","d"],
    "difficulty": "easy|medium|hard"
  }}
]

Max: {max_cloze}
"""

        text = self.groq.chat(sys, user, temperature=0.25, max_tokens=900)
        parsed = _parse_ai_json(text)

        if not isinstance(parsed, list):
            return []

        out = []
        for item in parsed[:max_cloze]:
            sent = (item.get("sentence") or "").strip()
            ans = (item.get("answer") or "").strip()
            opts = item.get("options") or []
            diff = (item.get("difficulty") or "medium").strip()

            if not sent or "_____" not in sent or not ans:
                continue

            # Enforce 4 unique options including the answer
            opts = [o for o in opts if o]
            if ans not in opts:
                opts = [ans] + opts
            unique_opts = []
            seen = set()
            for o in opts:
                key = o.strip().lower()
                if key and key not in seen:
                    unique_opts.append(o)
                    seen.add(key)
                if len(unique_opts) == 4:
                    break
            # Pad if needed
            while len(unique_opts) < 4:
                unique_opts.append(
                    ans + "s" if ans + "s" not in unique_opts else ans.upper()
                )

            out.append(
                {
                    "sentence": sent,
                    "correct_answer": ans,
                    "options": unique_opts[:4],
                    "difficulty": diff,
                    "hint": "Choose the word that fits best.",
                }
            )

        return out


# ---------------------------
# HIGH-LEVEL 3-CALL PIPELINE
# ---------------------------


def run_two_call_pipeline(
    transcript: str,
    limits: Optional[Dict[str, int]] = None,
    enhance_distractors: bool = True,
) -> Dict[str, Any]:
    """
    Production 3-call pipeline:

    Call 1: Extract vocabulary, mistakes, sentences (local extractors)
    Call 2: Generate all games (rule-based generators)
    Call 3: Enhance distractors with Groq (optional, single LLM call)

    The third call upgrades synthetic distractors (e.g., "goess", "eated")
    to semantic, pedagogically-sound alternatives (e.g., "walks", "consumed").

    Args:
        transcript: Lesson transcript text
        limits: Optional dict with limits per exercise type
        enhance_distractors: If True, call Groq to improve distractor quality

    Returns:
        Dict with all 6 exercise types, counts, and metadata.
    """
    from ..extractors import VocabularyExtractor, MistakeExtractor, SentenceExtractor
    from ..generators import (
        generate_flashcards,
        generate_spelling_items,
        generate_fill_blank,
        generate_sentence_builder,
        generate_grammar_challenge,
        generate_advanced_cloze,
    )

    limits = limits or {}
    flash_limit = int(limits.get("flashcards", 8))
    spelling_limit = int(limits.get("spelling", 8))
    fill_blank_limit = int(limits.get("fill_blank", 8))
    sentence_builder_limit = int(limits.get("sentence_builder", 3))
    grammar_challenge_limit = int(limits.get("grammar_challenge", 3))
    advanced_cloze_limit = int(limits.get("advanced_cloze", 2))

    # -----------------------------------------
    # CALL 1: Local extraction (no LLM cost)
    # -----------------------------------------
    vocabulary = VocabularyExtractor().extract(transcript)
    mistakes = MistakeExtractor().extract(transcript)
    sentences = SentenceExtractor().extract(transcript)

    logger.info(
        "Extraction complete: %d vocab, %d mistakes, %d sentences",
        len(vocabulary),
        len(mistakes),
        len(sentences),
    )

    # -----------------------------------------
    # CALL 2: Generation (rule-based, no LLM)
    # -----------------------------------------
    flashcards = generate_flashcards(vocabulary, transcript, limit=flash_limit)
    spelling = generate_spelling_items(vocabulary, transcript, limit=spelling_limit)
    fill_blank = generate_fill_blank(mistakes, transcript, limit=fill_blank_limit)
    sentence_builder = generate_sentence_builder(
        sentences, limit=sentence_builder_limit
    )
    grammar_challenge = generate_grammar_challenge(
        mistakes, limit=grammar_challenge_limit
    )
    advanced_cloze = generate_advanced_cloze(sentences, limit=advanced_cloze_limit)

    exercises = {
        "flashcards": flashcards,
        "spelling": spelling,
        "fill_blank": fill_blank,
        "sentence_builder": sentence_builder,
        "grammar_challenge": grammar_challenge,
        "advanced_cloze": advanced_cloze,
    }

    # -----------------------------------------
    # CALL 3: Enhance distractors with Groq (optional)
    # -----------------------------------------
    if enhance_distractors:
        try:
            from ..enhancers import enhance_pipeline_output

            logger.info("Enhancing distractors with Groq...")
            exercises = enhance_pipeline_output(exercises)
            logger.info("Distractor enhancement complete")
        except Exception as e:
            logger.warning("Distractor enhancement failed, using original: %s", e)
            # Keep original exercises on failure

    return {
        **exercises,
        "counts": {
            "flashcards": len(exercises.get("flashcards", [])),
            "spelling": len(exercises.get("spelling", [])),
            "fill_blank": len(exercises.get("fill_blank", [])),
            "sentence_builder": len(exercises.get("sentence_builder", [])),
            "grammar_challenge": len(exercises.get("grammar_challenge", [])),
            "advanced_cloze": len(exercises.get("advanced_cloze", [])),
        },
        "metadata": {
            "vocabulary_count": len(vocabulary),
            "mistakes_count": len(mistakes),
            "sentences_count": len(sentences),
            "distractors_enhanced": enhance_distractors,
        },
    }
