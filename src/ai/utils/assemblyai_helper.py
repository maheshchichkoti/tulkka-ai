# assemblyai_helper.py

import os
import logging
from typing import Optional, Dict
import time
import requests

try:
    import assemblyai as aai
    AAI_AVAILABLE = True
except ImportError:
    AAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class AssemblyAIHelper:
    """Production-ready AssemblyAI wrapper for transcription."""

    def __init__(self):
        self.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        self.base_url = os.getenv("ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com/v2").rstrip("/")

        if self.api_key and AAI_AVAILABLE:
            try:
                aai.settings.api_key = self.api_key
                self.enabled = True
                logger.info("AssemblyAI initialized successfully")
            except Exception as exc:
                logger.warning(f"AssemblyAI init failed: {exc}")
                self.enabled = False
        else:
            if not AAI_AVAILABLE:
                logger.info("assemblyai package not installed")
            if not self.api_key:
                logger.info("ASSEMBLYAI_API_KEY not found")
            self.enabled = False

    # ------------------------------------------------------------
    # HTTP-based fallback (bytes)
    # ------------------------------------------------------------
    def transcribe_audio_bytes(self, audio_bytes: bytes, language_code: str = "en") -> Optional[Dict]:
        if not self.api_key:
            logger.warning("ASSEMBLYAI_API_KEY not set")
            return None

        headers = {"authorization": self.api_key}

        # 1) upload
        upload_url = f"{self.base_url}/upload"
        try:
            r = requests.post(upload_url, headers=headers, data=audio_bytes, timeout=120)
            r.raise_for_status()
            uploaded_url = r.json().get("upload_url")
            if not uploaded_url:
                logger.error("AssemblyAI upload returned no upload_url")
                return None
        except Exception as exc:
            logger.error(f"AssemblyAI upload failed: {exc}")
            return None

        # 2) create job
        transcript_url = f"{self.base_url}/transcript"
        payload = {
            "audio_url": uploaded_url,
            "language_code": language_code,
            "punctuate": True,
            "format_text": True,
        }

        try:
            r = requests.post(transcript_url, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            job_id = r.json().get("id")
            if not job_id:
                logger.error("AssemblyAI transcript creation returned no id")
                return None
        except Exception as exc:
            logger.error(f"AssemblyAI transcript create failed: {exc}")
            return None

        # 3) poll
        status_url = f"{transcript_url}/{job_id}"
        max_wait = 600
        start = time.time()

        while True:
            if time.time() - start > max_wait:
                logger.error(f"Polling timeout for AssemblyAI job {job_id}")
                return None

            try:
                r = requests.get(status_url, headers=headers, timeout=15)
                r.raise_for_status()
                data = r.json()

                if data.get("status") == "completed":
                    text = data.get("text", "") or ""
                    job_id = data.get("id")
                    duration = data.get("audio_duration")
                    if text:
                        logger.info(
                            "AssemblyAI job %s completed with %d chars (duration=%s)",
                            job_id,
                            len(text),
                            duration,
                        )
                    else:
                        logger.warning(
                            "AssemblyAI job %s completed but returned empty text (duration=%s). "
                            "This usually means no speech was detected or the audio/language is unsupported.",
                            job_id,
                            duration,
                        )
                    return {
                        "text": text,
                        "id": job_id,
                        "status": data.get("status"),
                        "confidence": data.get("confidence"),
                        "duration": duration,
                    }

                if data.get("status") == "failed":
                    logger.error(f"AssemblyAI transcription failed: {data.get('error')}")
                    return None

            except Exception as exc:
                logger.warning(f"Poll error for job {job_id}: {exc}")

            time.sleep(2)

    # ------------------------------------------------------------
    # SDK-based URL transcription
    # ------------------------------------------------------------
    def transcribe_audio(self, audio_url: str, language_code: str = "en") -> Optional[Dict]:
        if not self.enabled:
            logger.warning("AssemblyAI SDK not available")
            return None

        try:
            config = aai.TranscriptionConfig(
                language_code=language_code,
                punctuate=True,
                format_text=True,
            )
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(audio_url)

            # wait for completion
            max_wait = 300
            start = time.time()

            while transcript.status not in ("completed", "error"):
                if time.time() - start > max_wait:
                    logger.error("Transcription timeout")
                    return None
                time.sleep(5)

            if transcript.status == "error":
                logger.error(f"AssemblyAI transcription error: {transcript.error}")
                return None

            return {
                "text": transcript.text,
                "id": transcript.id,
                "status": transcript.status,
                "confidence": getattr(transcript, "confidence", None),
                "duration": getattr(transcript, "audio_duration", None),
            }

        except Exception as exc:
            logger.error(f"AssemblyAI transcription failed: {exc}")
            return None

    # ------------------------------------------------------------
    # SDK-based local file transcription
    # ------------------------------------------------------------
    def transcribe_local_file(self, file_path: str, language_code: str = "en") -> Optional[Dict]:
        if not self.enabled:
            logger.warning("AssemblyAI SDK not available")
            return None

        try:
            config = aai.TranscriptionConfig(
                language_code=language_code,
                punctuate=True,
                format_text=True,
            )
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(file_path)

            max_wait = 300
            start = time.time()

            while transcript.status not in ("completed", "error"):
                if time.time() - start > max_wait:
                    logger.error("Transcription timeout")
                    return None
                time.sleep(5)

            if transcript.status == "error":
                logger.error(f"AssemblyAI transcription error: {transcript.error}")
                return None

            return {
                "text": transcript.text,
                "id": transcript.id,
                "status": transcript.status,
                "confidence": getattr(transcript, "confidence", None),
                "duration": getattr(transcript, "audio_duration", None),
            }

        except Exception as exc:
            logger.error(f"AssemblyAI transcription failed: {exc}")
            return None
