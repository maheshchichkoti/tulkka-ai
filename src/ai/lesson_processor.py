# src/ai/lesson_processor.py
"""Core lesson processing pipeline for generating exercises from transcripts."""

from __future__ import annotations
from typing import Dict, List, Any, Optional
import logging
import uuid
import re

from .extractors import VocabularyExtractor, MistakeExtractor, SentenceExtractor
from .generators import (
    generate_flashcards,
    generate_spelling_items,
    generate_fill_blank,
    generate_sentence_builder,
    generate_grammar_challenge,
    generate_advanced_cloze
)

logger = logging.getLogger(__name__)

class LessonProcessor:
    """
    Main processor for converting transcripts into learning exercises.
    
    Orchestrates extraction and generation phases to produce:
    - Flashcards (vocabulary)
    - Spelling items
    - Fill-in-the-blank exercises
    - Sentence builder exercises
    - Grammar challenges
    - Advanced cloze exercises
    """
    
    def __init__(self):
        self.vocab_extractor = VocabularyExtractor()
        self.mistake_extractor = MistakeExtractor()
        self.sentence_extractor = SentenceExtractor()
        self.quality_checker: Optional[Any] = None
        
        try:
            from .utils.quality_checker import QualityChecker
            self.quality_checker = QualityChecker()
        except ImportError:
            logger.debug("QualityChecker not available")
        except Exception as e:
            logger.warning("Failed to initialize QualityChecker: %s", e)

    def preprocess_data(
        self,
        vocabulary: List[Any],
        mistakes: List[Any],
        sentences: List[Any],
        transcript: str = "",
        lesson_number: int = 1,
    ) -> Dict[str, Any]:
        processed_vocab: List[Dict[str, Any]] = []
        processed_mistakes: List[Dict[str, Any]] = []
        processed_sentences: List[Dict[str, Any]] = []

        def find_example_sentence(word: str, text: str) -> str:
            if not text or not word:
                return ""
            parts = re.split(r'(?<=[.!?])\s+', text)
            lower = word.lower()
            for p in parts:
                if lower in p.lower():
                    return p.strip()
            return ""

        for i, item in enumerate(vocabulary or []):
            if isinstance(item, dict):
                word = item.get("word") or item.get("text") or item.get("id") or ""
                example = item.get("example_sentence") or item.get("example") or ""
                translation = item.get("translation") or ""
                item_id = str(item.get("id") or item.get("uuid") or f"vocab_{i}_{uuid.uuid4().hex[:8]}")
            else:
                word = str(item).strip()
                example = find_example_sentence(word, transcript)
                translation = ""
                item_id = f"vocab_{i}_{uuid.uuid4().hex[:8]}"
            if not word:
                continue
            processed_vocab.append({
                "id": item_id,
                "word": word,
                "example_sentence": example,
                "translation": translation,
                "source": "preprocess",
            })

        for i, s in enumerate(sentences or []):
            if isinstance(s, dict):
                sentence_text = s.get("sentence") or s.get("text") or s.get("english_sentence") or ""
                item_id = str(s.get("id") or s.get("uuid") or f"sent_{i}_{uuid.uuid4().hex[:8]}")
                translation = s.get("translation") or ""
            else:
                sentence_text = str(s).strip()
                item_id = f"sent_{i}_{uuid.uuid4().hex[:8]}"
                translation = ""
            if not sentence_text:
                continue
            processed_sentences.append({
                "id": item_id,
                "sentence": sentence_text,
                "english_sentence": sentence_text,
                "translation": translation,
            })

        for i, m in enumerate(mistakes or []):
            if isinstance(m, dict):
                raw = m.get("raw") or m.get("mistake") or m.get("text") or m.get("incorrect") or ""
                corrected = m.get("correct") or m.get("corrected") or m.get("fix") or m.get("suggestion") or ""
                hint = m.get("hint") or m.get("explanation") or ""
                item_id = str(m.get("id") or m.get("uuid") or f"mist_{i}_{uuid.uuid4().hex[:8]}")
            else:
                raw = str(m).strip()
                corrected = ""
                hint = ""
                item_id = f"mist_{i}_{uuid.uuid4().hex[:8]}"
            if not raw:
                continue
            processed_mistakes.append({
                "id": item_id,
                "raw": raw,
                "corrected": corrected,
                "hint": hint,
                "source": "preprocess",
            })

        return {
            "vocabulary": processed_vocab,
            "mistakes": processed_mistakes,
            "sentences": processed_sentences,
            "transcript": transcript or "",
            "lesson_number": lesson_number,
        }

    def process_lesson(self, transcript: str, lesson_number: int = 1) -> Dict:
        if not transcript or not transcript.strip():
            return self._empty(lesson_number)
        try:
            vocabulary = self.vocab_extractor.extract(transcript)
            mistakes = self.mistake_extractor.extract(transcript)
            sentences = self.sentence_extractor.extract(transcript)

            logger.info(f"Extracted: {len(vocabulary)} vocab, {len(mistakes)} mistakes, {len(sentences)} sentences")

            processed = self.preprocess_data(vocabulary, mistakes, sentences, transcript, lesson_number)
            vocab_struct = processed["vocabulary"]
            mistakes_struct = processed["mistakes"]
            sentences_struct = processed["sentences"]

            flashcards = generate_flashcards(vocab_struct, transcript, limit=8)
            spelling = generate_spelling_items(vocab_struct, transcript, limit=8)
            fill_blank = generate_fill_blank(mistakes_struct, transcript, limit=8)
            sentence_builder = generate_sentence_builder(sentences_struct, limit=3)
            grammar_challenge = generate_grammar_challenge(mistakes_struct, limit=3)
            advanced_cloze = generate_advanced_cloze(sentences_struct, limit=2)

            # Optional: enhance distractors with Groq for production-quality options
            exercises = {
                "flashcards": flashcards,
                "spelling": spelling,
                "fill_blank": fill_blank,
                "sentence_builder": sentence_builder,
                "grammar_challenge": grammar_challenge,
                "advanced_cloze": advanced_cloze,
            }

            try:
                from .enhancers import enhance_pipeline_output
                logger.info("Enhancing distractors with Groq for lesson %s...", lesson_number)
                exercises = enhance_pipeline_output(exercises)
            except Exception as e:
                # If Groq is unavailable or enhancement fails, keep original exercises
                logger.warning("Distractor enhancement skipped/failed: %s", e)

            flashcards = exercises.get("flashcards", flashcards)
            spelling = exercises.get("spelling", spelling)
            fill_blank = exercises.get("fill_blank", fill_blank)
            sentence_builder = exercises.get("sentence_builder", sentence_builder)
            grammar_challenge = exercises.get("grammar_challenge", grammar_challenge)
            advanced_cloze = exercises.get("advanced_cloze", advanced_cloze)

            qc_ok = True
            if self.quality_checker:
                try:
                    qc_ok = self.quality_checker.validate_exercises(fill_blank, flashcards, spelling)
                except Exception as e:
                    logger.warning("Quality check failed: %s", e)
                    qc_ok = False

            total_exercises = len(flashcards) + len(spelling) + len(fill_blank) + len(sentence_builder) + len(grammar_challenge) + len(advanced_cloze)

            return {
                "flashcards": flashcards,
                "spelling": spelling,
                "fill_blank": fill_blank,
                "sentence_builder": sentence_builder,
                "grammar_challenge": grammar_challenge,
                "advanced_cloze": advanced_cloze,
                "mistakes": mistakes_struct,
                "metadata": {
                    "lesson_number": lesson_number,
                    "status": "success",
                    "quality_passed": qc_ok,
                    "vocabulary_count": len(vocab_struct),
                    "mistakes_count": len(mistakes_struct),
                    "sentences_count": len(sentences_struct),
                    "total_exercises": total_exercises,
                }
            }
        except Exception as e:
            logger.exception("Lesson processing failed")
            return self._empty(lesson_number, error=str(e))

    def _empty(self, lesson_number: int, error: str = None):
        return {
            "flashcards": [],
            "spelling": [],
            "fill_blank": [],
            "sentence_builder": [],
            "grammar_challenge": [],
            "advanced_cloze": [],
            "mistakes": [],
            "metadata": {
                "lesson_number": lesson_number,
                "status": "error" if error else "empty",
                "error": error
            }
        }
