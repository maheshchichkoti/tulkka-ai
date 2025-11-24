"""Main orchestrator for lesson processing"""
from typing import Dict, List
import logging
from .extractors import VocabularyExtractor, MistakeExtractor, SentenceExtractor
from .generators import (
    generate_flashcards,
    generate_cloze,
    generate_grammar,
    generate_sentence_items
)

logger = logging.getLogger(__name__)

class LessonProcessor:
    """Main orchestrator for lesson processing"""
    
    def __init__(self):
        self.vocab_extractor = VocabularyExtractor()
        self.mistake_extractor = MistakeExtractor()
        self.sentence_extractor = SentenceExtractor()
        
        # Initialize quality checker
        try:
            from .utils.quality_checker import QualityChecker
            self.quality_checker = QualityChecker()
        except Exception as e:
            logger.warning(f"Could not initialize quality checker: {e}")
            self.quality_checker = None
    
    def process_lesson(self, transcript: str, lesson_number: int = 1) -> Dict:
        """Process lesson transcript and generate exercises"""
        
        logger.info(f"Processing lesson {lesson_number}")
        
        if not transcript or not transcript.strip():
            logger.warning(f"Empty transcript for lesson {lesson_number}")
            return {
                'flashcards': [],
                'cloze': [],
                'grammar': [],
                'sentence': [],
                'metadata': {'lesson_number': lesson_number, 'status': 'empty'}
            }
        
        try:
            # Step 1: Extract content
            logger.info("Extracting content...")
            vocabulary = self.vocab_extractor.extract(transcript)
            mistakes = self.mistake_extractor.extract(transcript)
            sentences = self.sentence_extractor.extract(transcript)
            
            logger.info(f"Extracted: {len(vocabulary)} vocab, {len(mistakes)} mistakes, {len(sentences)} sentences")
            
            # Step 2: Prepare text for generators
            # Step 3: Generate exercises with limits
            logger.info("Generating exercises...")
            
            flashcards = generate_flashcards(vocabulary, transcript, limit=12)
            cloze_items = generate_cloze(mistakes, transcript, limit=8)
            grammar_questions = generate_grammar(mistakes, limit=8)
            sentence_items = generate_sentence_items(sentences, limit=8)
            
            # Step 4: Balance exercise counts (aim for 20-30 total)
            total = len(flashcards) + len(cloze_items) + len(grammar_questions) + len(sentence_items)
            logger.info(f"Generated {total} exercises: {len(flashcards)} flashcards, {len(cloze_items)} cloze, {len(grammar_questions)} grammar, {len(sentence_items)} sentence")
            
            # Step 5: Quality check (if available)
            quality_passed = True
            if self.quality_checker:
                try:
                    # Convert dataclass objects to dicts for quality checker
                    def to_dict_for_qc(item):
                        if hasattr(item, 'to_dict'):
                            return item.to_dict()
                        elif isinstance(item, dict):
                            return item
                        else:
                            return item.__dict__ if hasattr(item, '__dict__') else {}

                    # Adapt cloze items into the fill-in-blank shape expected by QualityChecker
                    base_cloze = [to_dict_for_qc(c) for c in cloze_items]
                    fill_in_blank_items = []
                    for ex in base_cloze:
                        parts = ex.get('text_parts') or []
                        options_matrix = ex.get('options') or []
                        correct_list = ex.get('correct_answers') or []
                        if len(parts) != 2 or not options_matrix or not correct_list:
                            continue

                        # Options may be nested as a single list inside another list
                        first = options_matrix[0]
                        opts = first if isinstance(first, list) else options_matrix
                        if not isinstance(opts, list) or len(opts) < 3:
                            continue

                        correct_word = correct_list[0]
                        if not correct_word or correct_word not in opts:
                            continue

                        before = (parts[0] or '').strip()
                        after = (parts[1] or '').strip()
                        sentence = (before + " _____ " + after).strip()
                        # Skip very short fragments which QC will flag as too short
                        if len(sentence.split()) < 4:
                            continue

                        # Map options to option_a/option_b/... and determine correct_answer
                        letters = ["A", "B", "C", "D"]
                        option_fields = {}
                        for idx, opt in enumerate(opts[:4]):
                            option_fields[f"option_{letters[idx].lower()}"] = opt

                        try:
                            correct_index = opts.index(correct_word)
                        except ValueError:
                            continue
                        if correct_index > 3:
                            # Correct word is outside the exported A-D range
                            continue
                        correct_answer = letters[correct_index]

                        fill_in_blank_items.append({
                            'sentence': sentence,
                            'correct_answer': correct_answer,
                            'correct_word': correct_word,
                            **option_fields,
                        })

                    # Prepare flashcards for QC: ensure non-empty translation and an example sentence
                    raw_flashcards = [to_dict_for_qc(f) for f in flashcards]
                    flashcard_items = []
                    for card in raw_flashcards:
                        word = (card.get('word') or '').strip()
                        # Fallback: if translation missing, reuse the word so QC sees something non-empty
                        translation = (card.get('translation') or '').strip() or word
                        example = card.get('example_sentence') or card.get('notes') or card.get('context') or ''
                        flashcard_items.append({
                            **card,
                            'word': word,
                            'translation': translation,
                            'example_sentence': example,
                        })

                    quality_passed = self.quality_checker.validate_exercises(
                        fill_in_blank_items,  # treat adapted cloze as fill-in-blank
                        flashcard_items,
                        []  # no spelling in this flow
                    )
                    if not quality_passed:
                        logger.warning("Quality check failed - review recommended")
                except Exception as e:
                    logger.warning(f"Quality check error: {e}")
            
            # Convert dataclass objects to dicts (if they have to_dict method)
            def to_dict_safe(item):
                if hasattr(item, 'to_dict'):
                    return item.to_dict()
                elif isinstance(item, dict):
                    return item
                else:
                    return item.__dict__ if hasattr(item, '__dict__') else item
            
            return {
                'flashcards': [to_dict_safe(f) for f in flashcards],
                'cloze': [to_dict_safe(c) for c in cloze_items],
                'grammar': [to_dict_safe(g) for g in grammar_questions],
                'sentence': [to_dict_safe(s) for s in sentence_items],
                'mistakes': mistakes,
                'metadata': {
                    'lesson_number': lesson_number,
                    'total_exercises': total,
                    'vocabulary_count': len(vocabulary),
                    'mistakes_count': len(mistakes),
                    'sentences_count': len(sentences),
                    'quality_passed': quality_passed,
                    'status': 'success'
                }
            }
            
        except Exception as e:
            logger.exception(f"Error processing lesson {lesson_number}: {e}")
            return {
                'flashcards': [],
                'cloze': [],
                'grammar': [],
                'sentence': [],
                'metadata': {'lesson_number': lesson_number, 'status': 'error', 'error': str(e)}
            }

    def _sanitize_cloze(self, items: List) -> List:
        """Drop cloze items that cannot form a valid fill-in-blank sentence with options.

        This does not change the public structure of cloze items, only filters out
        fragments that would obviously fail quality checks (no options, missing
        correct answer, or sentences that are too short).
        """
        cleaned: List = []
        for item in items:
            # ClozeItem dataclass exposes attributes; dicts use keys
            parts = getattr(item, 'text_parts', None) if hasattr(item, 'text_parts') else None
            options = getattr(item, 'options', None) if hasattr(item, 'options') else None
            correct = getattr(item, 'correct_answers', None) if hasattr(item, 'correct_answers') else None
            if parts is None or options is None or correct is None:
                # Fallback for dict-like items
                as_dict = item.to_dict() if hasattr(item, 'to_dict') else (item or {})
                parts = as_dict.get('text_parts')
                options = as_dict.get('options')
                correct = as_dict.get('correct_answers')

            if not parts or len(parts) != 2 or not options or not correct:
                continue

            first = options[0]
            opts = first if isinstance(first, list) else options
            if not isinstance(opts, list) or len(opts) < 3:
                continue

            correct_word = correct[0] if isinstance(correct, list) and correct else None
            if not correct_word or correct_word not in opts:
                continue

            before = (parts[0] or '').strip()
            after = (parts[1] or '').strip()
            # Reconstruct full sentence to ensure it's not just a tiny fragment
            candidate_sentence = (before + ' ' + correct_word + ' ' + after).strip()
            if len(candidate_sentence.split()) < 4:
                continue

            cleaned.append(item)

        return cleaned
    
