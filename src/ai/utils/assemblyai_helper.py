"""AssemblyAI integration for audio transcription
Production-ready with error handling and fallback"""

import os
import logging
from typing import Optional, Dict
import time

try:
    import assemblyai as aai
    AAI_AVAILABLE = True
except ImportError:
    AAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class AssemblyAIHelper:
    """Production-ready AssemblyAI wrapper for transcription"""
    
    def __init__(self):
        """Initialize AssemblyAI client"""
        self.api_key = os.getenv('ASSEMBLYAI_API_KEY')
        self.base_url = os.getenv('ASSEMBLYAI_BASE_URL', 'https://api.assemblyai.com/v2')
        
        if self.api_key and AAI_AVAILABLE:
            try:
                aai.settings.api_key = self.api_key
                self.enabled = True
                logger.info("AssemblyAI initialized successfully")
            except Exception as e:
                logger.warning(f"AssemblyAI init failed: {e}")
                self.enabled = False
        else:
            if not AAI_AVAILABLE:
                logger.info("assemblyai package not installed")
            else:
                logger.info("ASSEMBLYAI_API_KEY not found")
            self.enabled = False
    
    def transcribe_audio(self, audio_url: str, language_code: str = "en") -> Optional[Dict]:
        """
        Transcribe audio file from URL
        
        Args:
            audio_url: URL to audio file
            language_code: Language code (default: en)
            
        Returns:
            Dict with transcript text and metadata, or None if failed
        """
        if not self.enabled:
            logger.warning("AssemblyAI not available")
            return None
        
        try:
            logger.info(f"Starting transcription for: {audio_url}")
            
            config = aai.TranscriptionConfig(
                language_code=language_code,
                punctuate=True,
                format_text=True
            )
            
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(audio_url)
            
            # Wait for completion
            max_wait = 300  # 5 minutes
            start_time = time.time()
            
            while transcript.status not in ['completed', 'error']:
                if time.time() - start_time > max_wait:
                    logger.error("Transcription timeout")
                    return None
                
                time.sleep(5)
                transcript = transcriber.get_transcript(transcript.id)
            
            if transcript.status == 'error':
                logger.error(f"Transcription error: {transcript.error}")
                return None
            
            logger.info(f"Transcription completed: {len(transcript.text)} chars")
            
            return {
                'text': transcript.text,
                'id': transcript.id,
                'status': transcript.status,
                'confidence': transcript.confidence if hasattr(transcript, 'confidence') else None,
                'duration': transcript.audio_duration if hasattr(transcript, 'audio_duration') else None
            }
            
        except Exception as e:
            logger.error(f"AssemblyAI transcription failed: {e}")
            return None
    
    def transcribe_local_file(self, file_path: str, language_code: str = "en") -> Optional[Dict]:
        """
        Transcribe local audio file
        
        Args:
            file_path: Path to local audio file
            language_code: Language code (default: en)
            
        Returns:
            Dict with transcript text and metadata, or None if failed
        """
        if not self.enabled:
            logger.warning("AssemblyAI not available")
            return None
        
        try:
            logger.info(f"Uploading and transcribing: {file_path}")
            
            config = aai.TranscriptionConfig(
                language_code=language_code,
                punctuate=True,
                format_text=True
            )
            
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(file_path)
            
            # Wait for completion
            max_wait = 300  # 5 minutes
            start_time = time.time()
            
            while transcript.status not in ['completed', 'error']:
                if time.time() - start_time > max_wait:
                    logger.error("Transcription timeout")
                    return None
                
                time.sleep(5)
            
            if transcript.status == 'error':
                logger.error(f"Transcription error: {transcript.error}")
                return None
            
            logger.info(f"Transcription completed: {len(transcript.text)} chars")
            
            return {
                'text': transcript.text,
                'id': transcript.id,
                'status': transcript.status,
                'confidence': transcript.confidence if hasattr(transcript, 'confidence') else None,
                'duration': transcript.audio_duration if hasattr(transcript, 'audio_duration') else None
            }
            
        except Exception as e:
            logger.error(f"AssemblyAI transcription failed: {e}")
            return None
