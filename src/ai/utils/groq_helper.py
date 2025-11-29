# src/ai/groq_pipeline.py
"""
Three-call Groq-based pipeline helpers for lesson processing.

Provides:
 - GroqMistakeGrammarExtractor
 - GroqVocabSentenceExtractor
 - GroqClozeGenerator
 - run_three_call_pipeline(...) helper

Design goals:
 - Single-responsibility classes
 - Clear JSON-first prompts (strict output)
 - Safe fallbacks to heuristics
 - Hebrew translations (simple dictionary style) via _build_translator/_translate when available
"""

from __future__ import annotations
import json
import logging
import os
import re
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# ---------------------------
# Lightweight Groq client wrapper
# ---------------------------
try:
    from groq import Groq  # optional dependency
    GROQ_AVAILABLE = True
except Exception:
    Groq = None  # type: ignore
    GROQ_AVAILABLE = False

class GroqClient:
    """Small wrapper around groq.Groq chat completions with safe parsing."""
    def __init__(self, model: Optional[str] = None):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.enabled = bool(self.api_key and GROQ_AVAILABLE)
        self.client = None
        if not self.enabled:
            if not self.api_key:
                logger.info("GROQ_API_KEY not set; Groq disabled.")
            elif not GROQ_AVAILABLE:
                logger.info("groq package not installed; Groq disabled.")
            return
        try:
            self.client = Groq(api_key=self.api_key)
            logger.info("GroqClient ready (%s)", self.model)
        except Exception as e:
            logger.exception("Failed to init Groq client: %s", e)
            self.enabled = False
            self.client = None

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 1200) -> Optional[str]:
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
            # Groq response shape may vary; be defensive
            if not resp or not getattr(resp, "choices", None):
                return None
            choice = resp.choices[0]
            # support both .message.content and .text
            content = getattr(getattr(choice, "message", None), "content", None) or getattr(choice, "content", None) or str(choice)
            return content
        except Exception as exc:
            msg = str(exc)
            # graceful handling of rate limits and model errors
            if "429" in msg or "rate limit" in msg.lower():
                logger.warning("Groq rate-limited: %s", msg)
            elif "decommission" in msg.lower() or "model" in msg.lower() and "decommission" in msg.lower():
                logger.error("Groq model error: %s", msg)
                self.enabled = False
                self.client = None
            else:
                logger.exception("Groq chat failed: %s", msg)
            return None

# ---------------------------
# Helpers
# ---------------------------
_JSON_RE = re.compile(r"(\{.*\}|\[.*\])", flags=re.DOTALL)

def _parse_ai_json(text: str) -> Optional[Any]:
    """Extract JSON blob from free text and parse it. Returns Python object or None."""
    if not text:
        return None
    # remove triple-backtick blocks and leading/trailing code fences
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    m = _JSON_RE.search(cleaned)
    payload = m.group(1) if m else cleaned
    try:
        return json.loads(payload)
    except Exception as e:
        logger.debug("AI JSON parse failed (%s). Trying safer eval fallback.", e)
        try:
            # last resort: replace single quotes with double for simple cases
            alt = re.sub(r"(?<!\\)'", '"', payload)
            return json.loads(alt)
        except Exception:
            logger.error("Failed to parse AI JSON response: %s", e)
            return None

def trim_transcript(transcript: str, max_chars: int = 4000) -> str:
    if not transcript:
        return ""
    t = transcript.strip()
    if len(t) <= max_chars:
        return t
    # prefer taking the middle portion (remove super-long intros) - preserves content variety
    start = max(0, (len(t) // 2) - (max_chars // 2))
    return t[start:start + max_chars]

# ---------------------------
# Translation helpers (reuse your existing translator if available)
# ---------------------------
def _build_translator_fallback(target_lang: str = "he"):
    """Try to import your existing translator builder from generators, else attempt deep_translator."""
    try:
        # your generators module exposes a builder in previous code; attempt import
        from .generators import _build_translator  # type: ignore
        return _build_translator(target_lang)
    except Exception:
        try:
            from deep_translator import GoogleTranslator
            normalized = target_lang if target_lang != "he" else "iw"
            return GoogleTranslator(source="en", target=normalized)
        except Exception:
            return None

def _translate_word(word: str, translator) -> str:
    if not word or not translator:
        return ""
    try:
        # If translator is deep_translator.GoogleTranslator: method is translate
        if hasattr(translator, "translate"):
            return translator.translate(word)
        # If your generator translator instance behaves differently, fallback to str()
        return str(word)
    except Exception as e:
        logger.debug("Translation failed for '%s': %s", word, e)
        return ""

# ---------------------------
# Groq-based extractors
# ---------------------------
class GroqMistakeGrammarExtractor:
    """Extract mistakes and grammar points from transcript using Groq (1 AI call)."""

    def __init__(self, groq: Optional[GroqClient] = None):
        self.groq = groq or GroqClient()
        self.enabled = bool(self.groq and self.groq.enabled)
        self.translator = _build_translator_fallback("he")

    def extract(self, transcript: str, max_mistakes: int = 12) -> Dict[str, List[Dict[str, str]]]:
        if not transcript:
            return {"mistakes": [], "grammar_points": []}
        if not self.enabled:
            logger.info("Groq disabled: falling back to heuristic MistakeExtractor")
            try:
                from .extractors import MistakeExtractor  # type: ignore
                me = MistakeExtractor()
                mistakes = me.extract(transcript)
                # grammar points best-effort: derive from mistake rule
                grammar_points = [{"rule": m.get("rule", ""), "example": m.get("correct", "")} for m in mistakes]
                return {"mistakes": mistakes[:max_mistakes], "grammar_points": grammar_points}
            except Exception:
                return {"mistakes": [], "grammar_points": []}

        prompt_sys = "You are an expert ESL teacher. Extract student mistakes and clear grammar teaching points."
        transcript_trim = trim_transcript(transcript, max_chars=3500)
        prompt_user = f"""
Transcript:
{transcript_trim}

Instructions:
1) Return a JSON object with keys "mistakes" (array) and "grammar_points" (array).
2) mistakes: list of objects with fields:
   - incorrect (student utterance, short)
   - correct (teacher correction or better form)
   - type (short tag e.g. grammar_verb_tense, grammar_article, vocabulary_word_form, etc.)
   - rule (brief rule in English)
   - context (short excerpt)
3) grammar_points: list of objects:
   - rule (short English rule)
   - example (example sentence or corrected phrase)
   - hebrew (single-word Hebrew summary/translation; if you can provide short Hebrew for the rule, include it)
4) Provide no other text. Output strictly as JSON.
5) Return up to {max_mistakes} mistakes and up to 8 grammar_points.
"""
        resp_text = self.groq.chat(prompt_sys, prompt_user, temperature=0.15, max_tokens=900)
        parsed = _parse_ai_json(resp_text) if resp_text else None
        if not isinstance(parsed, dict):
            logger.warning("Groq mistake/grammar extractor returned non-dict; fallback to heuristics.")
            return {"mistakes": [], "grammar_points": []}
        # Normalize and translate grammar_point hebrew field if missing
        grammar_points = []
        for g in parsed.get("grammar_points", []) or []:
            r = (g.get("rule") or "").strip()
            ex = (g.get("example") or "").strip()
            heb = (g.get("hebrew") or "").strip()
            if not heb and self.translator:
                heb = _translate_word(r, self.translator)
            grammar_points.append({"rule": r, "example": ex, "hebrew": heb})
        # Validate mistakes
        mistakes = []
        for m in parsed.get("mistakes", []) or []:
            incorrect = (m.get("incorrect") or "").strip()
            correct = (m.get("correct") or "").strip()
            typ = (m.get("type") or "grammar_general").strip()
            rule = (m.get("rule") or "").strip()
            ctx = (m.get("context") or "").strip()
            if not incorrect or not correct:
                continue
            mistakes.append({"incorrect": incorrect, "correct": correct, "type": typ, "rule": rule, "context": ctx})
            if len(mistakes) >= max_mistakes:
                break
        return {"mistakes": mistakes, "grammar_points": grammar_points}

class GroqVocabSentenceExtractor:
    """Extract vocabulary (with Hebrew) and practice sentences with one Groq call."""

    def __init__(self, groq: Optional[GroqClient] = None):
        self.groq = groq or GroqClient()
        self.enabled = bool(self.groq and self.groq.enabled)
        self.translator = _build_translator_fallback("he")

    def extract(self, transcript: str, max_vocab: int = 15, max_sentences: int = 12) -> Dict[str, List[Dict[str, str]]]:
        if not transcript:
            return {"vocabulary": [], "sentences": []}
        if not self.enabled:
            logger.info("Groq disabled: falling back to heuristic Vocabulary + Sentence extractors")
            try:
                from .extractors import VocabularyExtractor, SentenceExtractor  # type: ignore
                ve = VocabularyExtractor()
                se = SentenceExtractor()
                return {"vocabulary": ve.extract(transcript), "sentences": se.extract(transcript)}
            except Exception:
                return {"vocabulary": [], "sentences": []}

        prompt_sys = "You are an expert ESL teacher: extract high-value vocabulary and practice sentences. Provide Hebrew translations for vocabulary."
        transcript_trim = trim_transcript(transcript, max_chars=3500)
        prompt_user = f"""
Transcript:
{transcript_trim}

Instructions:
1) Output strictly JSON: an object with keys "vocabulary" and "sentences".
2) vocabulary: array of objects with fields:
   - word (single word or short phrase, 1-3 words)
   - hebrew (single-word Hebrew translation)
   - example (short example sentence using the word)
   - difficulty (easy|medium|hard)
3) sentences: array of objects with fields:
   - sentence (8-20 words)
   - difficulty (easy|medium|hard)
   - grammar_focus (e.g. past_simple, modal_verb, article)
4) Return up to {max_vocab} vocabulary items and up to {max_sentences} sentences.
"""
        resp_text = self.groq.chat(prompt_sys, prompt_user, temperature=0.2, max_tokens=1100)
        parsed = _parse_ai_json(resp_text) if resp_text else None
        if not isinstance(parsed, dict):
            logger.warning("Groq vocab/sentences extractor returned non-dict; fallback empty.")
            return {"vocabulary": [], "sentences": []}
        vocab = []
        for item in parsed.get("vocabulary", []) or []:
            word = (item.get("word") or "").strip()
            heb = (item.get("hebrew") or "").strip()
            example = (item.get("example") or "").strip()
            diff = (item.get("difficulty") or "medium").strip()
            if not word:
                continue
            if not heb and self.translator:
                heb = _translate_word(word, self.translator)
            vocab.append({"word": word, "hebrew": heb, "example": example, "difficulty": diff})
            if len(vocab) >= max_vocab:
                break
        sentences = []
        for s in parsed.get("sentences", []) or []:
            sentence = (s.get("sentence") or "").strip()
            diff = (s.get("difficulty") or "medium").strip()
            gf = (s.get("grammar_focus") or "").strip()
            if not sentence:
                continue
            sentences.append({"sentence": sentence, "difficulty": diff, "grammar_focus": gf})
            if len(sentences) >= max_sentences:
                break
        return {"vocabulary": vocab, "sentences": sentences}

class GroqClozeGenerator:
    """Generate cloze (fill-in-blank) items from chosen sentences/vocab (1 call)."""

    def __init__(self, groq: Optional[GroqClient] = None):
        self.groq = groq or GroqClient()
        self.enabled = bool(self.groq and self.groq.enabled)

    def generate(self, sentences: List[Dict[str, str]], vocabulary: List[Dict[str, str]], max_cloze: int = 8) -> List[Dict[str, Any]]:
        if not sentences:
            return []
        if not self.enabled:
            logger.info("Groq disabled: fallback simple cloze heuristic.")
            # naive heuristic: blank out one medium-length word per sentence
            outs = []
            for s in sentences[:max_cloze]:
                words = s["sentence"].split()
                # pick a word with len>3 preferably
                candidate = None
                for w in words:
                    if len(w.strip(".,?!")) > 4:
                        candidate = w.strip(".,?!")
                        break
                if not candidate:
                    candidate = words[len(words)//2].strip(".,?!")
                blank_sentence = s["sentence"].replace(candidate, "_____", 1)
                options = [candidate, candidate + "s", candidate + "ed", candidate.upper()]
                outs.append({"sentence": blank_sentence, "answer": candidate, "options": options[:4], "difficulty": s.get("difficulty", "medium")})
            return outs

        # Build JSON prompt
        # Provide candidate vocabulary to prioritize blanks, but allow AI to choose the best blanks
        vocab_list = [v["word"] for v in (vocabulary or [])][:20]
        prompt_sys = "You are an ESL exercise author. Create reliable cloze items (fill-in-the-blank)."
        sample_sentences = "\n".join([f"{i+1}. {s['sentence']}" for i, s in enumerate(sentences[:20])])
        prompt_user = f"""
Sentences (choose up to {max_cloze}):
{sample_sentences}

Vocabulary to prefer for blanks (optional):
{', '.join(vocab_list)}

Instructions:
1) Return JSON array of objects with fields:
   - sentence: the sentence with exactly one '_____' blank
   - answer: correct text that fills the blank
   - options: array of 3-4 distractors including the correct answer (order may be any)
   - difficulty: easy|medium|hard
2) Prefer blanks that test vocabulary/grammar from the transcript.
3) Output strictly JSON array.
"""
        resp_text = self.groq.chat(prompt_sys, prompt_user, temperature=0.25, max_tokens=900)
        parsed = _parse_ai_json(resp_text) if resp_text else None
        if not isinstance(parsed, list):
            logger.warning("Groq cloze generator returned non-list; fallback to heuristic.")
            return []
        out = []
        for item in parsed[:max_cloze]:
            sent = (item.get("sentence") or "").strip()
            ans = (item.get("answer") or "").strip()
            opts = item.get("options") or []
            diff = (item.get("difficulty") or "medium").strip()
            if not sent or "_____" not in sent or not ans:
                continue
            # ensure options contain answer
            opts = [o for o in opts if o]
            if ans not in opts:
                opts = [ans] + opts
            # normalize options to unique and max 4
            uniq = []
            seen = set()
            for o in opts:
                key = o.strip().lower()
                if key and key not in seen:
                    uniq.append(o)
                    seen.add(key)
                if len(uniq) == 4:
                    break
            out.append({"sentence": sent, "answer": ans, "options": uniq, "difficulty": diff})
        return out

# ---------------------------
# High-level helper
# ---------------------------
def run_three_call_pipeline(transcript: str, limits: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """
    Run the 3-call hybrid pipeline and return normalized structures:
    {
        "vocabulary": [...],
        "sentences": [...],
        "mistakes": [...],
        "grammar_points": [...],
        "cloze": [...]
    }
    """
    limits = limits or {}
    max_vocab = int(limits.get("vocabulary", 15))
    max_sentences = int(limits.get("sentences", 12))
    max_mistakes = int(limits.get("mistakes", 12))
    max_cloze = int(limits.get("cloze", 8))

    groq_client = GroqClient()
    mg_extractor = GroqMistakeGrammarExtractor(groq_client)
    vs_extractor = GroqVocabSentenceExtractor(groq_client)
    cloze_gen = GroqClozeGenerator(groq_client)

    # Call 1: mistakes + grammar
    mg = mg_extractor.extract(transcript, max_mistakes)
    mistakes = mg.get("mistakes", []) or []
    grammar_points = mg.get("grammar_points", []) or []

    # Call 2: vocabulary + sentences
    vs = vs_extractor.extract(transcript, max_vocab, max_sentences)
    vocabulary = vs.get("vocabulary", []) or []
    sentences = vs.get("sentences", []) or []

    # Call 3: cloze generation (sentences + vocabulary)
    cloze_items = cloze_gen.generate(sentences, vocabulary, max_cloze)

    return {
        "vocabulary": vocabulary,
        "sentences": sentences,
        "mistakes": mistakes,
        "grammar_points": grammar_points,
        "cloze": cloze_items
    }

# End of groq_pipeline.py
