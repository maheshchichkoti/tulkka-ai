#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick pipeline test - run with: python quick_test.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Real transcript from Teacher Philip lesson
TRANSCRIPT = """
Teacher Philip: Hello! Welcome to TOLCA Today.
Teacher Philip: How are you?
Sohel: Fine.
Teacher Philip: Good. What do you like to do? Do you like to ride a bike?
Sohel: play.
Teacher Philip: You like to play? What games do you like to play?
Sohel: Football.
Teacher Philip: Football, cool. Today, we will have some fun. We'll do a level test.
Teacher Philip: Hello, my name is Axie. What's your name?
Sohel: Hello, ma'am.
Teacher Philip: Good. I'm 7 years old. How old are you?
Sohel: I am 11 years old.
Teacher Philip: 11 years old, nice! I'm from the USA! Where are you from?
Sohel: I'm from Furaku.
Teacher Philip: Cool. Now we'll talk about hobbies!
Sohel: Hobbies.
Teacher Philip: Good. So, what are your hobbies?
Sohel: I want to play with my friends.
Teacher Philip: You play with a friend all day, right? Very fun.
Teacher Philip: Read! So, can you read English?
Sohel: My hobby is reading books. I love reading books.
Teacher Philip: Perfect. Watch.
Sohel: My hobby is watching TV, I love watching TV.
Teacher Philip: Good. Sing!
Sohel: My hobby is singing, and I love singing.
Teacher Philip: Good. Dance.
Sohel: My hobby is dancing, and I love dancing.
Teacher Philip: Good. Play sports.
Sohel: My hobby is playing sports. I love playing sports.
Teacher Philip: Good. Hiking.
Sohel: My hobby is hiking. I love hiking.
Teacher Philip: Good. Online games.
Sohel: My hobby is playing online games. I love playing online games.
Teacher Philip: Very good. What is he doing?
Sohel: Thinking.
Teacher Philip: What are they doing?
Sohel: Hiking.
Teacher Philip: Good, what are they doing?
Sohel: Watch.
Teacher Philip: Yeah, they're watching TV. Great!
Sohel: Reading book.
Teacher Philip: Yeah, they are reading.
Sohel: Dancing.
Teacher Philip: Dancing, good.
Sohel: play sports.
Teacher Philip: Yeah, they're playing sports, perfect.
Teacher Philip: Say, comfortable.
Sohel: Comfortable.
Teacher Philip: Pleasant.
Sohel: Pleasant.
Teacher Philip: Abandoned.
Sohel: Abandoned.
Teacher Philip: Perfect! Great! Wow, you have very good pronunciation! Amazing!
Teacher Philip: Your level is about an A2 level. A2 means you are a beginner.
Teacher Philip: But you are high beginner. Very high, high beginner.
Teacher Philip: Family festivals. The people in this family were eating special food.
Teacher Philip: They eat special foods when they celebrate.
Teacher Philip: Celebrate. So, celebrate is like a party.
Sohel: I watch fireworks.
Teacher Philip: Good, I watch fireworks when we celebrate!
Teacher Philip: We sing songs when they celebrate. Festival!
Sohel: decorate.
Teacher Philip: Perfect. Decorate the house with balloons.
Teacher Philip: This is a present!
Sohel: Present.
Teacher Philip: Good. Do you like to get presents?
Sohel: Yes.
Teacher Philip: This is a lamp.
Sohel: Lamp.
Teacher Philip: Good. The lamp was bright.
Sohel: Bright.
Teacher Philip: Dessert.
Sohel: Dessert.
Teacher Philip: It's a feast! A very large amount of food.
Sohel: Feast.
Teacher Philip: Good. There were small pies and cakes for dessert.
Teacher Philip: Festival is a special time when families get together.
Sohel: Festival.
Teacher Philip: A feast is a big meal with lots of special foods.
Teacher Philip: A lamp can help you see in the dark.
Sohel: Every year, family get together for festivals.
Teacher Philip: Good. Children help decorate the house.
Teacher Philip: Parents buy presents.
Teacher Philip: This family celebrates Diwali. They put lamps in their house.
Teacher Philip: During Hanukkah, this family lights one candle a day for 8 days.
Sohel: Play games and sing songs.
Teacher Philip: Perfect! Good job!
Teacher Philip: This family celebrates Chinese New Year. They clean the house.
Teacher Philip: Then wear red clothes and eat special foods.
Teacher Philip: What do parents buy for festivals?
Sohel: Presents.
Teacher Philip: Great job. The parents buy presents.
Teacher Philip: How many candles does one family light each day?
Sohel: 1.
Teacher Philip: You're right, one candle. Good.
Teacher Philip: What does one family wear when there is a new year?
Sohel: Red clothes.
Teacher Philip: Yeah. They wear red clothes. Good!
Teacher Philip: What do families not do at festivals?
Sohel: Play sports.
Teacher Philip: You're right. Good.
Teacher Philip: Great job today. Well done! Bye!
Sohel: Bye!
"""

def main():
    print("\n" + "="*60)
    print("  TULKKA PIPELINE QUICK TEST")
    print("="*60)
    
    # Test imports
    print("\n[1] Testing imports...")
    try:
        from src.ai.extractors import VocabularyExtractor, MistakeExtractor, SentenceExtractor
        from src.ai.generators import (
            generate_flashcards, generate_spelling_items, generate_fill_blank,
            generate_sentence_builder, generate_grammar_challenge, generate_advanced_cloze
        )
        from src.ai.lesson_processor import LessonProcessor
        print("    ✓ All imports successful")
    except Exception as e:
        print(f"    ✗ Import error: {e}")
        return 1
    
    # Test extraction
    print("\n[2] Testing extraction...")
    try:
        vocab = VocabularyExtractor().extract(TRANSCRIPT)
        mistakes = MistakeExtractor().extract(TRANSCRIPT)
        sentences = SentenceExtractor().extract(TRANSCRIPT)
        print(f"    ✓ Vocabulary: {len(vocab)} items")
        print(f"    ✓ Mistakes: {len(mistakes)} items")
        print(f"    ✓ Sentences: {len(sentences)} items")
    except Exception as e:
        print(f"    ✗ Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test generation
    print("\n[3] Testing generation...")
    try:
        flashcards = generate_flashcards(vocab, TRANSCRIPT, limit=8)
        spelling = generate_spelling_items(vocab, TRANSCRIPT, limit=8)
        fill_blank = generate_fill_blank(mistakes, TRANSCRIPT, limit=8)
        sentence_builder = generate_sentence_builder(sentences, limit=3)
        grammar = generate_grammar_challenge(mistakes, limit=3)
        adv_cloze = generate_advanced_cloze(sentences, limit=2)
        
        print(f"    ✓ Flashcards: {len(flashcards)}/8")
        print(f"    ✓ Spelling: {len(spelling)}/8")
        print(f"    ✓ Fill-blank: {len(fill_blank)}/8")
        print(f"    ✓ Sentence Builder: {len(sentence_builder)}/3")
        print(f"    ✓ Grammar Challenge: {len(grammar)}/3")
        print(f"    ✓ Advanced Cloze: {len(adv_cloze)}/2")
        
        total = len(flashcards) + len(spelling) + len(fill_blank) + len(sentence_builder) + len(grammar) + len(adv_cloze)
        print(f"\n    Total items: {total}/32")
    except Exception as e:
        print(f"    ✗ Generation error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test translation
    print("\n[4] Testing translation...")
    trans_count = sum(1 for fc in flashcards if fc.get("translation"))
    print(f"    Flashcards with Hebrew: {trans_count}/{len(flashcards)}")
    if trans_count > 0:
        print("    ✓ Translation working")
        sample = next((fc for fc in flashcards if fc.get("translation")), None)
        if sample:
            print(f"    Sample: {sample['word']} → {sample['translation']}")
    else:
        print("    ⚠ Translation not working (check deep_translator)")
    
    # Test full processor
    print("\n[5] Testing LessonProcessor...")
    try:
        processor = LessonProcessor()
        result = processor.process_lesson(TRANSCRIPT, lesson_number=1)
        
        counts = {
            "flashcards": len(result.get("flashcards", [])),
            "spelling": len(result.get("spelling", [])),
            "fill_blank": len(result.get("fill_blank", [])),
            "sentence_builder": len(result.get("sentence_builder", [])),
            "grammar_challenge": len(result.get("grammar_challenge", [])),
            "advanced_cloze": len(result.get("advanced_cloze", [])),
        }
        
        print(f"    ✓ LessonProcessor output:")
        for k, v in counts.items():
            print(f"      {k}: {v}")
        
        metadata = result.get("metadata", {})
        print(f"    Status: {metadata.get('status', 'N/A')}")
    except Exception as e:
        print(f"    ✗ Processor error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Sample output
    print("\n[6] Sample flashcard output:")
    if flashcards:
        import json
        print(json.dumps(flashcards[0], ensure_ascii=False, indent=2))
    
    print("\n" + "="*60)
    print("  TEST COMPLETED SUCCESSFULLY ✓")
    print("="*60 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
