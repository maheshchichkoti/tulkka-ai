# src/ai/enhancers/distractor_enhancer.py
"""
Distractor Enhancement Module

Upgrades rule-based distractors to semantic, pedagogically-sound alternatives
using a single LLM call. This transforms "synthetic ESL drill" quality into
"real academic material" quality.

Example transformation:
  Before: start → starting, starts, started (morphological noise)
  After:  start → begin, try, continue (semantic alternatives)
"""

from __future__ import annotations
import json
import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def _parse_json_safe(text: str) -> Optional[Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    if not text:
        return None
    
    # Remove markdown code blocks
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    cleaned = re.sub(r"```", "", cleaned).strip()
    
    # Try to find JSON array or object
    json_match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
    payload = json_match.group(1) if json_match else cleaned
    
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        # Try fixing single quotes
        try:
            fixed = re.sub(r"(?<!\\)'", '"', payload)
            return json.loads(fixed)
        except:
            return None


def enhance_distractors_with_groq(
    exercises: Dict[str, Any],
    groq_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Enhance all MCQ-style exercises with semantic distractors via Groq.
    
    Takes the full exercise dict and returns an enhanced version.
    Falls back to original if Groq fails or is unavailable.
    
    Args:
        exercises: Dict with fill_blank, grammar_challenge, advanced_cloze keys
        groq_client: Optional GroqClient instance (will create one if not provided)
    
    Returns:
        Enhanced exercises dict with better distractors
    """
    # Get or create Groq client
    if groq_client is None:
        try:
            from ..utils.groq_helper import GroqClient
            groq_client = GroqClient()
        except Exception as e:
            logger.warning("Could not create GroqClient: %s", e)
            return exercises
    
    if not groq_client or not groq_client.enabled:
        logger.info("Groq not available; skipping distractor enhancement")
        return exercises
    
    # Collect all items that need enhancement
    items_to_enhance = []
    
    # Fill blank items
    for i, item in enumerate(exercises.get("fill_blank", [])):
        items_to_enhance.append({
            "type": "fill_blank",
            "index": i,
            "sentence": item.get("sentence", ""),
            "correct": item.get("correct_answer", ""),
            "current_options": item.get("options", [])
        })
    
    # Grammar challenge items
    for i, item in enumerate(exercises.get("grammar_challenge", [])):
        items_to_enhance.append({
            "type": "grammar_challenge",
            "index": i,
            "sentence": item.get("prompt", ""),
            "correct": item.get("correct_answer", ""),
            "current_options": item.get("options", [])
        })
    
    # Advanced cloze items (two blanks each)
    for i, item in enumerate(exercises.get("advanced_cloze", [])):
        blank1 = item.get("blank1", {})
        blank2 = item.get("blank2", {})
        items_to_enhance.append({
            "type": "advanced_cloze_blank1",
            "index": i,
            "sentence": item.get("sentence", ""),
            "correct": blank1.get("correct", ""),
            "current_options": blank1.get("options", [])
        })
        items_to_enhance.append({
            "type": "advanced_cloze_blank2",
            "index": i,
            "sentence": item.get("sentence", ""),
            "correct": blank2.get("correct", ""),
            "current_options": blank2.get("options", [])
        })
    
    if not items_to_enhance:
        logger.info("No items to enhance")
        return exercises
    
    # Build the prompt
    items_json = json.dumps(items_to_enhance, indent=2)
    
    system_prompt = """You are an expert ESL curriculum designer. Your task is to generate high-quality distractors (wrong answer options) for multiple-choice exercises.

RULES:
1. Generate exactly 3 distractors + 1 correct answer = 4 options total
2. Distractors must be REAL English words (no nonsense like "goess", "eated", "thinked")
3. Distractors should be semantically plausible but grammatically or contextually wrong
4. For verbs: use real verbs that could fit but are wrong (e.g., "walks" instead of "goes")
5. For nouns: use related nouns (e.g., "package" instead of "letter")
6. Maintain appropriate difficulty level
7. The correct answer MUST be included in the options"""

    user_prompt = f"""Enhance these exercise items with better distractors.

Items to enhance:
{items_json}

For each item, return improved options that are:
- Real English words (never synthetic forms like "morninging" or "greated")
- Semantically related to the context
- Plausible but incorrect alternatives

Return ONLY a JSON array with this exact structure:
[
  {{
    "type": "fill_blank",
    "index": 0,
    "options": ["option1", "option2", "option3", "option4"]
  }},
  ...
]

The correct answer must be one of the 4 options. Order should be shuffled.
Return ONLY the JSON array, no other text."""

    try:
        response = groq_client.chat(
            system_prompt,
            user_prompt,
            temperature=0.3,
            max_tokens=2000
        )
        
        if not response:
            logger.warning("Empty response from Groq; keeping original distractors")
            return exercises
        
        enhanced_items = _parse_json_safe(response)
        
        if not isinstance(enhanced_items, list):
            logger.warning("Invalid response format from Groq; keeping original distractors")
            return exercises
        
        # Apply enhancements
        enhanced_exercises = _apply_enhancements(exercises, enhanced_items)
        
        logger.info("Successfully enhanced %d items with semantic distractors", len(enhanced_items))
        return enhanced_exercises
        
    except Exception as e:
        logger.exception("Distractor enhancement failed: %s", e)
        return exercises


def _apply_enhancements(
    exercises: Dict[str, Any],
    enhanced_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Apply enhanced options back to the exercises dict."""
    
    # Create a deep copy to avoid mutating original
    result = {
        "flashcards": list(exercises.get("flashcards", [])),
        "spelling": list(exercises.get("spelling", [])),
        "fill_blank": [dict(item) for item in exercises.get("fill_blank", [])],
        "sentence_builder": list(exercises.get("sentence_builder", [])),
        "grammar_challenge": [dict(item) for item in exercises.get("grammar_challenge", [])],
        "advanced_cloze": [dict(item) for item in exercises.get("advanced_cloze", [])],
    }
    
    for enhanced in enhanced_items:
        item_type = enhanced.get("type", "")
        index = enhanced.get("index", -1)
        new_options = enhanced.get("options", [])
        
        # Validate options
        if not new_options or len(new_options) < 4:
            continue
        
        # Ensure we have exactly 4 options
        new_options = new_options[:4]
        
        try:
            if item_type == "fill_blank" and 0 <= index < len(result["fill_blank"]):
                correct = result["fill_blank"][index].get("correct_answer", "")
                # Ensure correct answer is in options
                if correct and correct not in new_options:
                    new_options[0] = correct
                result["fill_blank"][index]["options"] = new_options
                
            elif item_type == "grammar_challenge" and 0 <= index < len(result["grammar_challenge"]):
                correct = result["grammar_challenge"][index].get("correct_answer", "")
                if correct and correct not in new_options:
                    new_options[0] = correct
                result["grammar_challenge"][index]["options"] = new_options
                
            elif item_type == "advanced_cloze_blank1" and 0 <= index < len(result["advanced_cloze"]):
                item = result["advanced_cloze"][index]
                if "blank1" not in item:
                    item["blank1"] = {}
                correct = item["blank1"].get("correct", "")
                if correct and correct not in new_options:
                    new_options[0] = correct
                item["blank1"]["options"] = new_options
                
            elif item_type == "advanced_cloze_blank2" and 0 <= index < len(result["advanced_cloze"]):
                item = result["advanced_cloze"][index]
                if "blank2" not in item:
                    item["blank2"] = {}
                correct = item["blank2"].get("correct", "")
                if correct and correct not in new_options:
                    new_options[0] = correct
                item["blank2"]["options"] = new_options
                
        except (IndexError, KeyError) as e:
            logger.warning("Could not apply enhancement for %s[%d]: %s", item_type, index, e)
            continue
    
    return result


# Convenience function for pipeline integration
def enhance_pipeline_output(exercises: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for pipeline integration.
    
    Call this after generating all exercises to upgrade distractor quality.
    Automatically handles Groq client creation and fallback.
    """
    return enhance_distractors_with_groq(exercises)
