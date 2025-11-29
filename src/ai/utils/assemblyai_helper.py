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
    """
    Production-ready AssemblyAI wrapper.
    - Handles large files with streaming upload
    - Retries on network errors / rate limits
    - Consistent structured logging
    - Supports SDK + HTTP fallback
    """

    MAX_RETRIES = 3
    RETRY_BACKOFF = [1, 2, 4]  # exponential backoff

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
    # Safe retry wrapper
    # ------------------------------------------------------------
    def _request_with_retry(self, method: str, url: str, **kwargs):
        for attempt in range(self.MAX_RETRIES):
            try:
                r = requests.request(method, url, timeout=60, **kwargs)

                # rate limited
                if r.status_code == 429:
                    wait_time = int(r.headers.get("Retry-After", 3))
                    logger.warning(f"429 rate limit, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue

                r.raise_for_status()
                return r

            except Exception as exc:
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(f"HTTP request failed after {self.MAX_RETRIES} attempts: {exc}")
                    return None

                logger.warning(
                    f"Attempt {attempt+1}/{self.MAX_RETRIES} failed: {exc}. Retrying in {self.RETRY_BACKOFF[attempt]}s"
                )
                time.sleep(self.RETRY_BACKOFF[attempt])

        return None

    # ------------------------------------------------------------
    # Streaming upload (safe for large audio files)
    # ------------------------------------------------------------
    def _upload_large_file(self, audio_bytes: bytes) -> Optional[str]:
        """Uploads chunks instead of loading entire file at once."""
        upload_url = f"{self.base_url}/upload"
        headers = {"authorization": self.api_key}

        CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks

        try:
            def chunk_generator():
                for i in range(0, len(audio_bytes), CHUNK_SIZE):
                    yield audio_bytes[i:i + CHUNK_SIZE]

            r = requests.post(upload_url, headers=headers, data=chunk_generator(), timeout=180)
            r.raise_for_status()

            uploaded_url = r.json().get("upload_url")
            if not uploaded_url:
                logger.error("AssemblyAI upload returned no upload_url")
                return None

            logger.info("Uploaded audio to AssemblyAI")
            return uploaded_url

        except Exception as exc:
            logger.error(f"AssemblyAI upload failed: {exc}")
            return None

    # ------------------------------------------------------------
    # HTTP-based transcription
    # ------------------------------------------------------------
    def transcribe_audio_bytes(self, audio_bytes: bytes, language_code: str = "en") -> Optional[Dict]:
        if not self.api_key:
            logger.warning("ASSEMBLYAI_API_KEY not set")
            return None

        # 1) upload using streaming safe method
        uploaded_url = self._upload_large_file(audio_bytes)
        if not uploaded_url:
            return None

        # 2) create job
        transcript_url = f"{self.base_url}/transcript"
        headers = {"authorization": self.api_key}
        payload = {
            "audio_url": uploaded_url,
            "language_code": language_code,
            "punctuate": True,
            "format_text": True,
        }

        r = self._request_with_retry("POST", transcript_url, json=payload, headers=headers)
        if not r:
            return None

        job_id = r.json().get("id")
        if not job_id:
            logger.error("AssemblyAI transcript creation returned no id")
            return None

        # 3) poll
        status_url = f"{transcript_url}/{job_id}"
        max_wait = 600
        start = time.time()
        last_log = 0

        while True:
            now = time.time()

            # Show progress every 10 seconds
            if now - last_log > 10:
                logger.info(f"Polling AssemblyAI job {job_id}...")
                last_log = now

            if now - start > max_wait:
                logger.error(f"Polling timeout for AssemblyAI job {job_id}")
                return None

            r = self._request_with_retry("GET", status_url, headers=headers)
            if not r:
                return None

            data = r.json()
            status = data.get("status")

            if status == "completed":
                text = data.get("text", "") or ""
                duration = data.get("audio_duration")

                if text:
                    logger.info(f"AssemblyAI job {job_id} completed with {len(text)} chars")
                else:
                    logger.warning(
                        f"AssemblyAI job {job_id} completed but empty text (duration={duration})"
                    )

                return {
                    "text": text,
                    "id": job_id,
                    "status": status,
                    "confidence": data.get("confidence"),
                    "duration": duration,
                }

            if status == "error" or status == "failed":
                logger.error(f"AssemblyAI transcription failed: {data.get('error')}")
                return None

            time.sleep(2)

    # ------------------------------------------------------------
    # SDK-based URL transcription (unchanged, but kept clean)
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
