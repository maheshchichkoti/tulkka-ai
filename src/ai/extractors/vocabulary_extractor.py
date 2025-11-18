"""Vocabulary extraction from lesson transcripts"""
from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)

class VocabularyExtractor:
    """Extracts key vocabulary and phrases from lessons"""
    
    def __init__(self):
        self.skip_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'can', 'could', 'should', 'may', 'might', 'must', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'this', 'that', 'these', 'those'
        }
        
        # Try to initialize Groq helper
        try:
            from ..utils.groq_helper import GroqHelper
            self.ai_helper = GroqHelper()
        except Exception as e:
            logger.warning(f"Could not initialize Groq helper: {e}")
            self.ai_helper = None
    
    def extract(self, transcript: str) -> List[Dict[str, str]]:
        """Extract vocabulary items from transcript"""
        # Try Groq AI first if available
        if self.ai_helper and self.ai_helper.enabled:
            try:
                ai_vocab = self.ai_helper.extract_vocabulary(transcript, max_words=15)
                if ai_vocab:
                    logger.info(f"Using {len(ai_vocab)} Groq AI vocabulary items")
                    return ai_vocab
            except Exception as e:
                logger.warning(f"Groq extraction failed, falling back to rule-based: {e}")
        
        # Fallback to rule-based extraction
        vocabulary = []
        seen = set()
        
        # Extract from corrections (highest priority)
        corrections = self._extract_corrections(transcript)
        for incorrect, correct in corrections:
            words = self._extract_key_words(correct)
            for word in words:
                normalized_word = word.split()[0] if ' ' in word else word
                if normalized_word.lower() not in seen:
                    vocabulary.append({
                        'word': normalized_word,
                        'context': correct,
                        'category': 'corrected_usage',
                        'priority': 'high'
                    })
                    seen.add(normalized_word.lower())
        
        # Extract explicit vocabulary mentions
        for line in transcript.split('\n'):
            vocab_pattern = r'(?:important|key|vocabulary|words?):\s*([^.]+)'
            match = re.search(vocab_pattern, line, re.IGNORECASE)
            if match:
                words_str = match.group(1)
                words = re.split(r',|\band\b', words_str)
                for word in words:
                    word = word.strip()
                    if word and word.lower() not in seen and len(word) > 2:
                        vocabulary.append({
                            'word': word,
                            'context': line,
                            'category': 'explicit_vocabulary',
                            'priority': 'high'
                        })
                        seen.add(word.lower())
        
        # Extract content words (nouns, verbs, adjectives)
        sentences = [s.strip() for s in transcript.split('.') if s.strip()]
        for sentence in sentences[:20]:  # Limit to first 20 sentences
            words = self._extract_key_words(sentence)
            for word in words[:3]:  # Top 3 per sentence
                if word.lower() not in seen and len(word) > 4:
                    vocabulary.append({
                        'word': word,
                        'context': sentence,
                        'category': 'content_word',
                        'priority': 'medium'
                    })
                    seen.add(word.lower())
                    if len(vocabulary) >= 20:
                        break
            if len(vocabulary) >= 20:
                break
        
        return vocabulary[:15]  # Return top 15
    
    def _extract_corrections(self, transcript: str) -> List[tuple]:
        """Extract correction patterns"""
        corrections = []
        patterns = [
            r"not\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:it's|say|use)\s+['\"]([^'\"]+)['\"]",
            r"don't say\s+['\"]([^'\"]+)['\"]\s*,?\s*say\s+['\"]([^'\"]+)['\"]",
            r"instead of\s+['\"]([^'\"]+)['\"]\s*,?\s*(?:use|say)\s+['\"]([^'\"]+)['\"]",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                corrections.append((match.group(1), match.group(2)))
        return corrections
    
    def _extract_key_words(self, text: str) -> List[str]:
        """Extract meaningful words from text"""
        words = []
        tokens = text.split()
        for token in tokens:
            clean = re.sub(r'[^\w\s-]', '', token).strip()
            if clean and len(clean) > 3 and clean.lower() not in self.skip_words:
                if clean[0].isupper() or len(clean) > 6:
                    words.append(clean)
        return words
