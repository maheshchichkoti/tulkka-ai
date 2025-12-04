"""
Gemini-based transcription and summary generation.

This module provides transcription and summary generation using Google's Gemini model.
Based on the Hugging Face Space implementation for Tulkka.

Primary transcription method with AssemblyAI as fallback.
"""

import os
import logging
import tempfile
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field

try:
    from google import genai

    GENAI_NEW_SDK_AVAILABLE = True
except ImportError:
    GENAI_NEW_SDK_AVAILABLE = False

try:
    import soundfile as sf

    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# Prompts (from docs/prompts.py)
# ============================================================================

TRANSCRIPTION_PROMPT = """You are given a conversation between a student and a teacher. The teacher is trying to teach english. 
Generate a transcript, always following the given format:
[timestamp] Speaker name(teacher or student): transcription
eg:
[12:26] teacher: hello!

Keep the segments short. There may be parts spoken in languages other than English. Transcribe them accurately using English Latin letters only and always provide their English translation alongside. For example: Yofi(good). 
"""

SUMMARY_PROMPT = """You are given conversation between a student and a teacher. The teacher is trying to teach english.  Return summary of the conversation. The summary should include:
 - topic: describe what the teacher is trying to teach in 30 words  (grammar or vocabulary or reading practice etc). Exclude irrelevant details related to classroom activities.
 - conversation: provide detailed decription of the conversation in around 300 words. Start from the beginning and include what the teacher said, what the student said, and any questions asked by either of them along with their responses, what was correct and what was not. There may be parts spoken in languages other than English. Transcribe them accurately using English Latin letters only and always provide their English translation alongside.
 - level: describe student's possible levels(give a range) in CEFR levels stating if the student seems a beginner, intermediate or an expert. Also tell about student's pronunciation ability and speaking speed(slow, normal or fast). 
"""

try:
    from docs.prompts import (
        transcription_prompt as external_transcription_prompt,
        summary_prompt as external_summary_prompt,
    )

    TRANSCRIPTION_PROMPT = external_transcription_prompt
    SUMMARY_PROMPT = external_summary_prompt
except Exception as exc:
    logger.warning(f"Failed to import prompts from docs.prompts: {exc}")


# ============================================================================
# Schema (from docs/schema.py)
# ============================================================================


class Summary(BaseModel):
    """Summary schema for Gemini structured output."""

    topic: str = Field(description="Description of what teacher is trying to teach.")
    conversation: str = Field(description="Details of the conversation.")
    level: str = Field(description="Student's level")


try:
    from docs.schema import Summary as ExternalSummary

    Summary = ExternalSummary
except Exception as exc:
    logger.warning(f"Failed to import Summary from docs.schema: {exc}")


# ============================================================================
# GeminiTranscriptionHelper class
# ============================================================================


class GeminiTranscriptionHelper:
    """
    Production-ready Gemini transcription wrapper.

    Uses Google's new genai SDK for audio transcription and summarization.
    Supports both file path and audio bytes input.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self):
        """Initialize Gemini transcription helper."""
        # Support multiple env var names for compatibility with Space code
        self.api_key = (
            os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("gemini")
        )
        self.model_name = os.getenv("GEMINI_TRANSCRIPTION_MODEL", self.DEFAULT_MODEL)

        if self.api_key and GENAI_NEW_SDK_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.enabled = True
                logger.info(
                    f"GeminiTranscriptionHelper initialized with model: {self.model_name}"
                )
            except Exception as exc:
                logger.warning(f"Gemini transcription init failed: {exc}")
                self.client = None
                self.enabled = False
        else:
            if not GENAI_NEW_SDK_AVAILABLE:
                logger.info("google-genai package not installed for transcription")
            if not self.api_key:
                logger.info("GOOGLE_API_KEY/GEMINI_API_KEY not found for transcription")
            self.client = None
            self.enabled = False

    def _save_temp_wav(
        self, audio_tuple: Tuple[int, Any], filename: str = None
    ) -> Optional[str]:
        """
        Save audio tuple (sample_rate, audio_data) to a temporary WAV file.

        Args:
            audio_tuple: Tuple of (sample_rate, audio_data) from Gradio or similar
            filename: Optional filename, defaults to temp file

        Returns:
            Path to the saved WAV file, or None if failed
        """
        if audio_tuple is None:
            return None

        if not SOUNDFILE_AVAILABLE:
            logger.error("soundfile package not available for audio conversion")
            return None

        try:
            sample_rate, audio_data = audio_tuple

            if filename is None:
                fd, filename = tempfile.mkstemp(suffix=".wav")
                os.close(fd)

            sf.write(filename, audio_data, sample_rate)
            logger.debug(f"Saved audio to temp file: {filename}")
            return filename

        except Exception as exc:
            logger.error(f"Failed to save audio to WAV: {exc}")
            return None

    def _save_bytes_to_temp(
        self, audio_bytes: bytes, suffix: str = ".wav"
    ) -> Optional[str]:
        """
        Save audio bytes to a temporary file.

        Args:
            audio_bytes: Raw audio bytes
            suffix: File extension

        Returns:
            Path to the saved file, or None if failed
        """
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)

            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)

            logger.debug(f"Saved {len(audio_bytes)} bytes to temp file: {tmp_path}")
            return tmp_path

        except Exception as exc:
            logger.error(f"Failed to save audio bytes to temp file: {exc}")
            return None

    def transcribe_audio_file(
        self, file_path: str, language_hint: str = None
    ) -> Optional[str]:
        """
        Transcribe audio from a file path using Gemini.

        Args:
            file_path: Path to the audio file
            language_hint: Optional language hint (not used by Gemini, but kept for API consistency)

        Returns:
            Transcription text, or None if failed
        """
        if not self.enabled:
            logger.warning("Gemini transcription not enabled")
            return None

        try:
            # Upload file to Gemini
            logger.info(f"Uploading audio file to Gemini: {file_path}")
            uploaded_file = self.client.files.upload(file=file_path)

            # Generate transcription
            logger.info("Generating transcription with Gemini...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[TRANSCRIPTION_PROMPT, uploaded_file],
                config={"temperature": 0.1},
            )

            if response and response.text:
                transcript = response.text.strip()
                logger.info(f"Gemini transcription completed: {len(transcript)} chars")
                return transcript
            else:
                logger.warning("Gemini returned empty transcription response")
                return None

        except Exception as exc:
            logger.error(f"Gemini transcription failed: {exc}")
            return None

    def transcribe_audio_bytes(
        self, audio_bytes: bytes, language_hint: str = None
    ) -> Optional[str]:
        """
        Transcribe audio from bytes using Gemini.

        Args:
            audio_bytes: Raw audio bytes (WAV, MP3, M4A, etc.)
            language_hint: Optional language hint

        Returns:
            Transcription text, or None if failed
        """
        if not self.enabled:
            logger.warning("Gemini transcription not enabled")
            return None

        # Detect file type from magic bytes
        suffix = ".wav"
        if audio_bytes[:4] == b"fLaC":
            suffix = ".flac"
        elif audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
            suffix = ".mp3"
        elif audio_bytes[4:8] == b"ftyp":
            suffix = ".m4a"

        # Save to temp file
        tmp_path = self._save_bytes_to_temp(audio_bytes, suffix=suffix)
        if not tmp_path:
            return None

        try:
            result = self.transcribe_audio_file(tmp_path, language_hint)
            return result
        finally:
            # Cleanup temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def transcribe_audio_tuple(
        self, audio_tuple: Tuple[int, Any], language_hint: str = None
    ) -> Optional[str]:
        """
        Transcribe audio from a Gradio-style tuple (sample_rate, audio_data).

        Args:
            audio_tuple: Tuple of (sample_rate, audio_data)
            language_hint: Optional language hint

        Returns:
            Transcription text, or None if failed
        """
        if not self.enabled:
            logger.warning("Gemini transcription not enabled")
            return None

        # Save to temp WAV file
        tmp_path = self._save_temp_wav(audio_tuple)
        if not tmp_path:
            return None

        try:
            result = self.transcribe_audio_file(tmp_path, language_hint)
            return result
        finally:
            # Cleanup temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def generate_summary(
        self, audio_bytes: bytes = None, audio_file: str = None
    ) -> Optional[Dict[str, str]]:
        """
        Generate a structured summary from audio using Gemini.

        Args:
            audio_bytes: Raw audio bytes (provide either this or audio_file)
            audio_file: Path to audio file (provide either this or audio_bytes)

        Returns:
            Dictionary with 'topic', 'conversation', 'level' keys, or None if failed
        """
        if not self.enabled:
            logger.warning("Gemini transcription not enabled")
            return None

        tmp_path = None
        cleanup_needed = False

        try:
            # Determine file path
            if audio_file:
                tmp_path = audio_file
            elif audio_bytes:
                tmp_path = self._save_bytes_to_temp(audio_bytes)
                cleanup_needed = True
                if not tmp_path:
                    return None
            else:
                logger.error("No audio provided for summary generation")
                return None

            # Upload file to Gemini
            logger.info(f"Uploading audio for summary generation: {tmp_path}")
            uploaded_file = self.client.files.upload(file=tmp_path)

            # Generate summary with structured output
            logger.info("Generating summary with Gemini...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[SUMMARY_PROMPT, uploaded_file],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": Summary,
                    "temperature": 0.1,
                },
            )

            if response and response.parsed:
                summary_dict = response.parsed.model_dump()
                logger.info(
                    f"Gemini summary generated: topic={summary_dict.get('topic', '')[:50]}..."
                )
                return summary_dict
            else:
                logger.warning("Gemini returned empty summary response")
                return None

        except Exception as exc:
            logger.error(f"Gemini summary generation failed: {exc}")
            return None
        finally:
            # Cleanup temp file if we created it
            if cleanup_needed and tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def generate_summary_from_transcript(
        self, transcript: str
    ) -> Optional[Dict[str, str]]:
        """
        Generate a structured summary from an existing transcript text.

        Args:
            transcript: The transcript text to summarize

        Returns:
            Dictionary with 'topic', 'conversation', 'level' keys, or None if failed
        """
        if not self.enabled:
            logger.warning("Gemini transcription not enabled")
            return None

        try:
            # Modify prompt for text input
            text_summary_prompt = SUMMARY_PROMPT.replace(
                "You are given conversation between a student and a teacher.",
                "You are given a transcript of a conversation between a student and a teacher.",
            )

            logger.info("Generating summary from transcript with Gemini...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    text_summary_prompt,
                    transcript[:10000],
                ],  # Limit transcript length
                config={
                    "response_mime_type": "application/json",
                    "response_schema": Summary,
                    "temperature": 0.1,
                },
            )

            if response and response.parsed:
                summary_dict = response.parsed.model_dump()
                logger.info("Gemini summary from transcript generated")
                return summary_dict
            else:
                logger.warning("Gemini returned empty summary response")
                return None

        except Exception as exc:
            logger.error(f"Gemini summary from transcript failed: {exc}")
            return None
