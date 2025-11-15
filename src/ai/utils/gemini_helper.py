"""Google Gemini AI integration for content extraction
Production-ready with optimized prompts and comprehensive error handling"""

import os
from typing import List, Dict, Optional
import logging
import json
import re

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class GeminiHelper:
    """Production-ready Gemini AI wrapper with optimized prompts"""
    
    def __init__(self, prompt_style: str = 'detailed'):
        """
        Initialize Gemini AI helper
        
        Args:
            prompt_style: 'detailed', 'simple', or 'role' for A/B testing
        """
        self.api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.prompt_style = prompt_style
        
        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                model_name = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash-exp")
                self.model = genai.GenerativeModel(model_name)
                self.enabled = True
                logger.info(f"Gemini AI initialized with {prompt_style} prompts")
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}. Using fallback.")
                self.enabled = False
                self.model = None
        else:
            if not GENAI_AVAILABLE:
                logger.info("google-generativeai package not installed. Using rule-based fallback.")
            else:
                logger.info("GOOGLE_API_KEY not found. Using rule-based fallback.")
            self.enabled = False
            self.model = None
    
    def extract_vocabulary_with_ai(self, transcript: str, max_words: int = 15) -> List[Dict[str, str]]:
        """Extract vocabulary using optimized AI prompts"""
        
        if not self.enabled or not self.model:
            logger.debug("Gemini AI not available, using fallback")
            return []
        
        try:
            prompt = f"""Analyze this conversation transcript and extract the most important English vocabulary words that would help an intermediate learner.

Instructions:
1. Identify {max_words} useful English words or phrases (prioritize mistakes, key topics, and practical expressions).
2. For each item include:
   - "word": the vocabulary word or phrase
   - "context": a simple example sentence from the transcript (or create a natural sentence if needed)
   - "difficulty": "beginner", "intermediate", or "advanced"

Transcript:
{transcript[:2500]}

Format your response EXACTLY as a JSON array. Example:
[
  {{"word": "breakfast", "context": "I eat breakfast at 8 AM.", "difficulty": "beginner"}},
  {{"word": "comfortable", "context": "The hotel was very comfortable.", "difficulty": "intermediate"}}
]

Return ONLY the JSON array with no extra commentary."""
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON response
            vocab_list = self._parse_json_response(result_text)
            
            if vocab_list:
                # Validate quality
                validated = self._validate_vocabulary(vocab_list, transcript)
                logger.info(f"Gemini AI extracted {len(validated)} vocabulary words")
                return validated[:max_words]
            else:
                logger.warning("Could not parse Gemini response")
                return []
                
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning(f"Gemini API quota exceeded - using fallback extraction")
            else:
                logger.error(f"Gemini AI vocabulary extraction failed: {e}")
            return []
    
    def extract_sentences_with_ai(self, transcript: str, max_sentences: int = 10) -> List[Dict[str, str]]:
        """Extract quality practice sentences using Gemini AI"""
        
        if not self.enabled or not self.model:
            logger.debug("Gemini AI not available for sentence extraction")
            return []
        
        try:
            prompt = f"""Extract {max_sentences} high-quality English sentences from this lesson transcript that are suitable for language practice exercises.

Transcript:
{transcript[:4000]}

Select sentences that:
1. Are grammatically correct and complete
2. Are 8-20 words long (not too short, not too long)
3. Contain useful vocabulary or grammar patterns
4. Are clear and natural-sounding
5. Represent different topics/contexts from the lesson

For each sentence provide:
- "sentence": the complete sentence
- "difficulty": "beginner", "intermediate", or "advanced"
- "grammar_focus": main grammar point (e.g., "present simple", "past tense", "prepositions")

Format your response EXACTLY as a JSON array:
[
  {{"sentence": "I wake up at 7 AM every morning.", "difficulty": "beginner", "grammar_focus": "present simple"}},
  {{"sentence": "Yesterday I went to the market with my mother.", "difficulty": "intermediate", "grammar_focus": "past simple"}}
]

Return ONLY the JSON array with no extra text."""

            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                logger.warning("Empty response from Gemini sentence extraction")
                return []
            
            text = response.text.strip()
            # Remove markdown code blocks if present
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            
            sentences_data = json.loads(text)
            
            if not isinstance(sentences_data, list):
                logger.warning("Gemini returned non-list for sentences")
                return []
            
            # Convert to expected format
            result = []
            for item in sentences_data[:max_sentences]:
                if isinstance(item, dict) and 'sentence' in item:
                    result.append({
                        'sentence': item['sentence'],
                        'source': 'gemini_ai',
                        'quality_score': 9,
                        'difficulty': item.get('difficulty', 'beginner'),
                        'grammar_focus': item.get('grammar_focus', '')
                    })
            
            logger.info(f"Gemini AI extracted {len(result)} sentences")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini sentence JSON: {e}")
            return []
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning(f"Gemini API quota exceeded - using fallback extraction")
            else:
                logger.error(f"Gemini AI sentence extraction failed: {e}")
            return []
    
    def _parse_json_response(self, text: str, expect_array: bool = True) -> Optional[any]:
        """Parse JSON from AI response with error handling"""
        try:
            # Remove markdown code blocks if present
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            
            # Try to find JSON in response
            if expect_array:
                json_match = re.search(r'\[.*\]', text, re.DOTALL)
            else:
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
            
            if json_match:
                return json.loads(json_match.group())
            else:
                # Try parsing entire text
                return json.loads(text)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return None
    
    def _validate_vocabulary(self, vocab_list: List[Dict], transcript: str) -> List[Dict]:
        """Validate and filter vocabulary results"""
        validated = []
        seen_words = set()
        
        # Common words to exclude
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                     'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that'}
        
        for item in vocab_list:
            word = item.get('word', '').lower().strip()
            
            # Validation checks
            if not word:
                continue
            if word in stop_words:
                continue
            if word in seen_words:
                continue
            if len(word) < 2 or len(word) > 30:
                continue
            
            # Ensure required fields
            if 'context' not in item:
                item['context'] = f"Example with {word}"
            if 'difficulty' not in item:
                item['difficulty'] = 'intermediate'
            
            validated.append(item)
            seen_words.add(word)
        
        return validated
