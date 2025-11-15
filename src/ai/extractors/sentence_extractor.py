"""Sentence extraction from lesson transcripts"""
from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)

class SentenceExtractor:
    """Extracts practice-worthy sentences from lessons"""
    
    def __init__(self):
        self.min_words = 4
        self.max_words = 20
        
        # Try to initialize Gemini helper
        try:
            from ..utils.gemini_helper import GeminiHelper
            self.gemini_helper = GeminiHelper()
        except Exception as e:
            logger.warning(f"Could not initialize Gemini helper: {e}")
            self.gemini_helper = None
    
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        """Extract sentences suitable for practice"""
        # Try Gemini AI first if available
        if self.gemini_helper and self.gemini_helper.enabled:
            try:
                ai_sentences = self.gemini_helper.extract_sentences_with_ai(transcript, max_sentences=15)
                if ai_sentences:
                    logger.info(f"Using {len(ai_sentences)} AI-extracted sentences")
                    return ai_sentences
            except Exception as e:
                logger.warning(f"Gemini extraction failed, falling back to rule-based: {e}")
        
        # Fallback to rule-based extraction
        sentences = []
        seen = set()
        
        # Split into sentences
        raw_sentences = [s.strip() for s in transcript.split('.') if s.strip()]
        
        for sentence in raw_sentences:
            # Clean sentence
            clean = sentence.strip()
            if not clean:
                continue
            
            # Count words
            words = clean.split()
            word_count = len(words)
            
            # Filter by length
            if word_count < self.min_words or word_count > self.max_words:
                continue
            
            # Skip if seen
            key = clean.lower()
            if key in seen:
                continue
            
            # Check if it's a good practice sentence
            if self._is_practice_worthy(clean):
                sentences.append({
                    'sentence': clean,
                    'word_count': word_count,
                    'difficulty': self._assess_difficulty(clean),
                    'type': self._classify_sentence(clean)
                })
                seen.add(key)
            
            if len(sentences) >= 15:
                break
        
        return sentences
    
    def _is_practice_worthy(self, sentence: str) -> bool:
        """Check if sentence is worth practicing"""
        # Must have a verb
        verb_patterns = [
            r'\b(is|are|was|were|have|has|had|do|does|did|will|would|can|could|should)\b',
            r'\b\w+(ed|ing|s)\b'
        ]
        has_verb = any(re.search(p, sentence, re.IGNORECASE) for p in verb_patterns)
        
        # Must not be a question (for now)
        is_question = sentence.strip().endswith('?')
        
        # Must have some content words
        content_words = [w for w in sentence.split() if len(w) > 4]
        has_content = len(content_words) >= 2
        
        return has_verb and not is_question and has_content
    
    def _assess_difficulty(self, sentence: str) -> str:
        """Assess sentence difficulty"""
        words = sentence.split()
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        if avg_word_length < 4:
            return 'easy'
        elif avg_word_length < 6:
            return 'medium'
        else:
            return 'hard'
    
    def _classify_sentence(self, sentence: str) -> str:
        """Classify sentence type"""
        if re.search(r'\b(is|are|was|were)\b', sentence, re.IGNORECASE):
            return 'be_verb'
        elif re.search(r'\b(have|has|had)\b', sentence, re.IGNORECASE):
            return 'have_verb'
        elif re.search(r'\b(will|would|can|could|should|may|might)\b', sentence, re.IGNORECASE):
            return 'modal_verb'
        else:
            return 'action_verb'
