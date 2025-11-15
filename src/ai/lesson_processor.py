"""Main orchestrator for lesson processing"""
from typing import Dict, List
import logging
from .extractors import VocabularyExtractor, MistakeExtractor, SentenceExtractor
from .generators import (
    generate_flashcards_from_text,
    generate_cloze_from_text,
    generate_grammar_from_text,
    generate_sentence_items_from_text
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
            paragraphs = self._split_into_paragraphs(transcript)
            
            # Step 3: Generate exercises with limits
            logger.info("Generating exercises...")
            
            flashcards = self._generate_flashcards(vocabulary, sentences, limit=8)
            cloze_items = self._generate_cloze(paragraphs, vocabulary, limit=6)
            grammar_questions = self._generate_grammar(paragraphs, mistakes, limit=6)
            sentence_items = self._generate_sentences(sentences, limit=6)
            
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
                    
                    cloze_dicts = [to_dict_for_qc(c) for c in cloze_items]
                    flashcard_dicts = [to_dict_for_qc(f) for f in flashcards]
                    
                    quality_passed = self.quality_checker.validate_exercises(
                        cloze_dicts,  # treat cloze as fill-in-blank
                        flashcard_dicts,
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
    
    def _split_into_paragraphs(self, transcript: str) -> List[str]:
        """Split transcript into paragraphs"""
        # Split by double newlines or long sentences
        paragraphs = []
        current = []
        
        for line in transcript.split('\n'):
            line = line.strip()
            if not line:
                if current:
                    paragraphs.append(' '.join(current))
                    current = []
            else:
                current.append(line)
                if len(' '.join(current)) > 500:
                    paragraphs.append(' '.join(current))
                    current = []
        
        if current:
            paragraphs.append(' '.join(current))
        
        return paragraphs if paragraphs else [transcript]
    
    def _generate_flashcards(self, vocabulary: List[Dict], sentences: List[Dict], limit: int) -> List[Dict]:
        """Generate flashcards from vocabulary"""
        flashcards = []
        
        for vocab_item in vocabulary[:limit]:
            flashcards.append({
                'word': vocab_item['word'],
                'translation': '',  # Would need translation API
                'notes': vocab_item.get('context', '')[:100],
                'category': vocab_item.get('category', 'general'),
                'priority': vocab_item.get('priority', 'medium')
            })
        
        return flashcards
    
    def _generate_cloze(self, paragraphs: List[str], vocabulary: List[Dict], limit: int) -> List[Dict]:
        """Generate cloze exercises"""
        return generate_cloze_from_text(paragraphs, max_items=limit, difficulty='medium')
    
    def _generate_grammar(self, paragraphs: List[str], mistakes: List[Dict], limit: int) -> List[Dict]:
        """Generate grammar questions"""
        return generate_grammar_from_text(paragraphs, max_questions=limit, difficulty='medium')
    
    def _generate_sentences(self, sentences: List[Dict], limit: int) -> List[Dict]:
        """Generate sentence builder exercises"""
        # Convert sentence dicts to strings
        sentence_texts = [s['sentence'] for s in sentences if 'sentence' in s]
        paragraphs = ['. '.join(sentence_texts)]
        return generate_sentence_items_from_text(paragraphs, max_items=limit, difficulty='medium')
