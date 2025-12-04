"""
AssemblyAI Transcription Quality Test Script
Tests transcription quality for ClassAudio.m4a
"""

import os
import sys
import time
import json
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import requests

# Configuration
API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
BASE_URL = os.getenv("ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com/v2").rstrip("/")
AUDIO_FILE = Path(__file__).parent / "ClassAudio(1).m4a"


def upload_audio(file_path: Path) -> str:
    """Upload audio file to AssemblyAI and return the upload URL."""
    print(f"\n📤 Uploading audio file: {file_path.name}")
    print(f"   File size: {file_path.stat().st_size / (1024*1024):.2f} MB")
    
    headers = {"authorization": API_KEY}
    
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/upload",
            headers=headers,
            data=f,
            timeout=300
        )
    
    response.raise_for_status()
    upload_url = response.json().get("upload_url")
    print(f"   ✅ Upload complete!")
    return upload_url


def create_transcript(audio_url: str) -> str:
    """Create a transcription job and return the transcript ID."""
    print("\n🎙️ Creating transcription job...")
    
    headers = {"authorization": API_KEY}
    payload = {
        "audio_url": audio_url,
        "language_detection": True,  # Auto-detect language
        "punctuate": True,
        "format_text": True,
        "speaker_labels": True,  # Identify different speakers
        "auto_chapters": True,   # Generate chapters
        "entity_detection": True,  # Detect entities (names, places, etc.)
        "sentiment_analysis": True,  # Analyze sentiment
    }
    
    response = requests.post(
        f"{BASE_URL}/transcript",
        headers=headers,
        json=payload,
        timeout=60
    )
    
    response.raise_for_status()
    transcript_id = response.json().get("id")
    print(f"   ✅ Job created: {transcript_id}")
    return transcript_id


def poll_transcript(transcript_id: str) -> dict:
    """Poll for transcript completion and return the result."""
    print("\n⏳ Waiting for transcription to complete...")
    
    headers = {"authorization": API_KEY}
    status_url = f"{BASE_URL}/transcript/{transcript_id}"
    
    start_time = time.time()
    last_status = ""
    
    while True:
        response = requests.get(status_url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        status = data.get("status")
        elapsed = time.time() - start_time
        
        if status != last_status:
            print(f"   Status: {status} ({elapsed:.1f}s elapsed)")
            last_status = status
        
        if status == "completed":
            print(f"   ✅ Transcription completed in {elapsed:.1f}s")
            return data
        
        if status == "error":
            print(f"   ❌ Error: {data.get('error')}")
            sys.exit(1)
        
        time.sleep(3)


def analyze_quality(result: dict):
    """Analyze and display transcription quality metrics."""
    print("\n" + "="*60)
    print("📊 TRANSCRIPTION QUALITY ANALYSIS")
    print("="*60)
    
    # Basic info
    text = result.get("text", "")
    confidence = result.get("confidence")
    audio_duration = result.get("audio_duration")
    language = result.get("language_code")
    
    print(f"\n📝 BASIC METRICS:")
    print(f"   • Language Detected: {language or 'N/A'}")
    print(f"   • Audio Duration: {audio_duration:.1f}s ({audio_duration/60:.1f} min)" if audio_duration else "   • Audio Duration: N/A")
    print(f"   • Overall Confidence: {confidence*100:.1f}%" if confidence else "   • Overall Confidence: N/A")
    print(f"   • Total Characters: {len(text):,}")
    print(f"   • Word Count: {len(text.split()):,}")
    
    # Word-level confidence analysis
    words = result.get("words", [])
    if words:
        confidences = [w.get("confidence", 0) for w in words if w.get("confidence")]
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            min_conf = min(confidences)
            max_conf = max(confidences)
            low_conf_words = [w for w in words if w.get("confidence", 1) < 0.7]
            
            print(f"\n🔤 WORD-LEVEL ANALYSIS:")
            print(f"   • Total Words Detected: {len(words):,}")
            print(f"   • Average Word Confidence: {avg_conf*100:.1f}%")
            print(f"   • Min Word Confidence: {min_conf*100:.1f}%")
            print(f"   • Max Word Confidence: {max_conf*100:.1f}%")
            print(f"   • Low Confidence Words (<70%): {len(low_conf_words)}")
            
            if low_conf_words[:10]:
                print(f"\n   ⚠️ Sample Low Confidence Words:")
                for w in low_conf_words[:10]:
                    print(f"      - \"{w.get('text')}\" ({w.get('confidence', 0)*100:.1f}%)")
    
    # Speaker analysis
    utterances = result.get("utterances", [])
    if utterances:
        speakers = set(u.get("speaker") for u in utterances)
        print(f"\n👥 SPEAKER ANALYSIS:")
        print(f"   • Speakers Detected: {len(speakers)}")
        for speaker in sorted(speakers):
            speaker_utterances = [u for u in utterances if u.get("speaker") == speaker]
            speaker_words = sum(len(u.get("text", "").split()) for u in speaker_utterances)
            print(f"   • {speaker}: {len(speaker_utterances)} utterances, ~{speaker_words} words")
    
    # Chapters
    chapters = result.get("chapters", [])
    if chapters:
        print(f"\n📚 AUTO-GENERATED CHAPTERS:")
        for i, ch in enumerate(chapters, 1):
            start_sec = ch.get("start", 0) / 1000
            end_sec = ch.get("end", 0) / 1000
            headline = ch.get("headline", "")
            print(f"   {i}. [{start_sec:.0f}s - {end_sec:.0f}s] {headline}")
    
    # Entities
    entities = result.get("entities", [])
    if entities:
        entity_types = {}
        for e in entities:
            etype = e.get("entity_type", "unknown")
            entity_types[etype] = entity_types.get(etype, 0) + 1
        
        print(f"\n🏷️ ENTITIES DETECTED:")
        for etype, count in sorted(entity_types.items(), key=lambda x: -x[1]):
            print(f"   • {etype}: {count}")
    
    # Sentiment
    sentiment_results = result.get("sentiment_analysis_results", [])
    if sentiment_results:
        sentiments = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
        for s in sentiment_results:
            sentiment = s.get("sentiment", "NEUTRAL")
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        
        total = sum(sentiments.values())
        print(f"\n😊 SENTIMENT ANALYSIS:")
        for sentiment, count in sentiments.items():
            pct = (count / total * 100) if total > 0 else 0
            print(f"   • {sentiment}: {count} ({pct:.1f}%)")
    
    # Full transcript
    print("\n" + "="*60)
    print("📜 FULL TRANSCRIPT:")
    print("="*60)
    print(text if text else "(No text transcribed)")
    
    # Save results to file
    output_file = Path(__file__).parent / "transcription_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Full result saved to: {output_file}")


def main():
    print("="*60)
    print("🎯 AssemblyAI Transcription Quality Test")
    print("="*60)
    
    # Validate
    if not API_KEY:
        print("❌ Error: ASSEMBLYAI_API_KEY not set in environment")
        sys.exit(1)
    
    if not AUDIO_FILE.exists():
        print(f"❌ Error: Audio file not found: {AUDIO_FILE}")
        sys.exit(1)
    
    print(f"\n🔑 API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"🎵 Audio File: {AUDIO_FILE}")
    
    try:
        # Step 1: Upload
        upload_url = upload_audio(AUDIO_FILE)
        
        # Step 2: Create transcript
        transcript_id = create_transcript(upload_url)
        
        # Step 3: Poll for completion
        result = poll_transcript(transcript_id)
        
        # Step 4: Analyze quality
        analyze_quality(result)
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text if e.response else 'N/A'}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
