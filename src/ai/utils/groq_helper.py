"""Groq LLM integration for lesson content extraction."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, List, Optional

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    Groq = None  # type: ignore
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)


class GroqHelper:
    """Wrapper around Groq chat completions for AI-assisted extraction."""

    def __init__(self, model: Optional[str] = None):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_name = model or os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.enabled = bool(self.api_key and GROQ_AVAILABLE)
        if not self.enabled:
            if not self.api_key:
                logger.info("GROQ_API_KEY not found. Falling back to heuristics.")
            elif not GROQ_AVAILABLE:
                logger.info("groq package not installed. Falling back to heuristics.")
            self.client = None
            return

        try:
            self.client = Groq(api_key=self.api_key)
            logger.info("Groq helper initialized with model %s", self.model_name)
        except Exception as exc:  # pragma: no cover - network failure
            logger.warning("Failed to initialize Groq client: %s", exc)
            self.client = None
            self.enabled = False

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def extract_vocabulary(self, transcript: str, max_words: int = 15) -> List[Dict[str, str]]:
        if not self._is_ready():
            return []

        system_prompt = (
            "You are an expert ESL teacher. Extract the most important vocabulary "
            "words or short phrases from lesson transcripts."
        )
        user_prompt = f"""
Transcript:
{transcript[:2500]}

Instructions:
1. Return up to {max_words} words/phrases useful for learners.
2. Prioritize corrections, mistakes, key concepts, and practical expressions.
3. Output strictly as JSON array with objects containing word, context, difficulty.
"""

        response_text = self._chat(system_prompt, user_prompt)
        vocab = self._parse_json(response_text, expect_array=True) if response_text else None
        if not isinstance(vocab, list):
            return []

        cleaned: List[Dict[str, str]] = []
        seen = set()
        for item in vocab[:max_words]:
            if not isinstance(item, dict):
                continue
            word = item.get("word", "").strip()
            if not word or word.lower() in seen:
                continue
            cleaned.append(
                {
                    "word": word,
                    "context": item.get("context") or f"Sample usage of {word}",
                    "difficulty": item.get("difficulty", "intermediate"),
                }
            )
            seen.add(word.lower())

        logger.info("Groq extracted %d vocabulary items", len(cleaned))
        return cleaned

    def extract_sentences(self, transcript: str, max_sentences: int = 10) -> List[Dict[str, str]]:
        if not self._is_ready():
            return []

        system_prompt = (
            "You curate high-quality English practice sentences from transcripts."
        )
        user_prompt = f"""
Transcript:
{transcript[:4000]}

Instructions:
1. Return up to {max_sentences} sentences between 8 and 20 words.
2. Sentences must be natural, grammatically correct, and helpful for practice.
3. Output JSON array with objects: sentence, difficulty, grammar_focus.
"""

        response_text = self._chat(system_prompt, user_prompt)
        sentences = self._parse_json(response_text, expect_array=True) if response_text else None
        if not isinstance(sentences, list):
            return []

        result: List[Dict[str, str]] = []
        for item in sentences[:max_sentences]:
            if not isinstance(item, dict):
                continue
            sentence = item.get("sentence")
            if not sentence:
                continue
            result.append(
                {
                    "sentence": sentence.strip(),
                    "difficulty": item.get("difficulty", "beginner"),
                    "grammar_focus": item.get("grammar_focus", ""),
                    "source": "groq_ai",
                    "quality_score": 9,
                }
            )

        logger.info("Groq extracted %d sentences", len(result))
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_ready(self) -> bool:
        if not self.enabled or not self.client:
            logger.debug("Groq helper not enabled; skipping AI extraction")
            return False
        return True

    def _chat(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if not self._is_ready():
            return None
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=1024,  # Fixed: Groq uses 'max_tokens', not 'max_output_tokens'
            )
            return resp.choices[0].message.content if resp.choices else None
        except Exception as exc:  # pragma: no cover - network failure
            msg = str(exc)
            # Gracefully handle quota and decommissioned models
            if "429" in msg or "rate limit" in msg.lower():
                logger.warning("Groq quota exceeded: %s", msg)
            elif "model_decommissioned" in msg or "model `llama3-70b-8192` has been decommissioned" in msg:
                logger.error("Groq model decommissioned: %s. Disabling Groq helper and falling back to heuristics.", msg)
                # Disable further Groq usage so pipeline keeps working with heuristic generators
                self.enabled = False
                self.client = None
            else:
                logger.error("Groq chat request failed: %s", msg)
            return None

    def _parse_json(self, text: str, expect_array: bool = True) -> Optional[object]:
        if not text:
            return None
        try:
            cleaned = re.sub(r"```json\s*|```", "", text).strip()
            match = re.search(r"\[.*\]" if expect_array else r"\{.*\}", cleaned, re.DOTALL)
            payload = match.group(0) if match else cleaned
            return json.loads(payload)
        except Exception as exc:
            logger.error("Failed to parse Groq JSON: %s", exc)
            return None
