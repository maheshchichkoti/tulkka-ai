# src/ai/transcription.py
"""
Transcription utilities.

Supports:
- using an uploaded Zoom transcript file (VTT/TXT) if provided
- Gemini (primary) for audio transcription when GOOGLE_API_KEY is set
- AssemblyAI (fallback) for audio transcription when ASSEMBLYAI_API_KEY is set
- pluggable: callers may pass their own transcribe_fn for custom provider

Functions:
- transcribe_recording(record_row, assemblyai_client=None, transcribe_fn=None)
- transcribe_audio_with_fallback(audio_bytes) - Gemini primary, AssemblyAI fallback
"""

from __future__ import annotations
import logging
import time
from typing import Optional, Dict, Any, Callable
import requests
from ..config import settings
from ..zoom.zoom_utils import clean_vtt_transcript, has_transcript_file, has_audio_files
from ..time_utils import utc_now_iso

logger = logging.getLogger(__name__)


# ============================================================================
# Gemini Transcription (Primary)
# ============================================================================


def _transcribe_with_gemini(
    audio_bytes: bytes, language_hint: str = None
) -> Optional[str]:
    """
    Transcribe audio using Gemini (primary method).

    Args:
        audio_bytes: Raw audio bytes
        language_hint: Optional language hint (not used by Gemini)

    Returns:
        Transcription text, or None if failed
    """
    try:
        from .utils.gemini_transcription_helper import GeminiTranscriptionHelper

        helper = GeminiTranscriptionHelper()
        if not helper.enabled:
            logger.debug("Gemini transcription not enabled, skipping")
            return None

        result = helper.transcribe_audio_bytes(audio_bytes, language_hint)
        if result:
            logger.info(f"Gemini transcription successful: {len(result)} chars")
            return result
        else:
            logger.warning("Gemini transcription returned empty result")
            return None

    except ImportError as e:
        logger.debug(f"Gemini transcription helper not available: {e}")
        return None
    except Exception as e:
        logger.warning(f"Gemini transcription failed: {e}")
        return None


# ============================================================================
# Combined Transcription with Fallback
# ============================================================================


def transcribe_audio_with_fallback(
    audio_bytes: bytes,
    language_hint: str = None,
    assemblyai_api_key: str = None,
) -> Dict[str, Any]:
    """
    Transcribe audio using Gemini (primary) with AssemblyAI fallback.

    Flow:
    1. Try Gemini transcription first
    2. If Gemini fails, fall back to AssemblyAI
    3. If both fail, raise TranscriptionError

    Args:
        audio_bytes: Raw audio bytes
        language_hint: Optional language hint
        assemblyai_api_key: Optional AssemblyAI API key (defaults to settings)

    Returns:
        Dict with 'text', 'source' ('gemini' or 'assemblyai'), and 'metadata'

    Raises:
        TranscriptionError if all methods fail
    """
    errors = []

    # 1. Try Gemini (primary)
    logger.info("Attempting transcription with Gemini (primary)...")
    try:
        gemini_result = _transcribe_with_gemini(audio_bytes, language_hint)
        if gemini_result:
            return {
                "text": gemini_result,
                "source": "gemini",
                "metadata": {
                    "model": settings.GEMINI_TRANSCRIPTION_MODEL,
                    "method": "primary",
                },
            }
    except Exception as e:
        errors.append(f"Gemini: {e}")
        logger.warning(f"Gemini transcription failed: {e}")

    # 2. Fallback to AssemblyAI
    logger.info("Gemini failed or unavailable, falling back to AssemblyAI...")
    api_key = assemblyai_api_key or settings.ASSEMBLYAI_API_KEY
    if api_key:
        try:
            text = _transcribe_with_assemblyai_audio_bytes(audio_bytes, api_key)
            if text:
                return {
                    "text": text,
                    "source": "assemblyai",
                    "metadata": {"method": "fallback"},
                }
        except Exception as e:
            errors.append(f"AssemblyAI: {e}")
            logger.warning(f"AssemblyAI transcription failed: {e}")
    else:
        errors.append("AssemblyAI: API key not configured")
        logger.debug("AssemblyAI API key not configured, skipping fallback")

    # 3. All methods failed
    error_msg = "; ".join(errors) if errors else "No transcription method available"
    raise TranscriptionError(f"All transcription methods failed: {error_msg}")


class TranscriptionError(Exception):
    pass


def _download_url(url: str, timeout: int = 120) -> bytes:
    resp = requests.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()
    return resp.content


def _transcribe_with_assemblyai_audio_bytes(
    audio_bytes: bytes, api_key: str, base_url: str = None, timeout: int = 120
) -> str:
    """
    Lightweight AssemblyAI flow:
    1) upload audio -> get upload_url
    2) create transcript job
    3) poll for completion
    Returns transcript text (plain).
    This function is conservative: if env key not present, it raises.
    """
    if not api_key:
        raise TranscriptionError("AssemblyAI API key not provided")

    base = base_url or settings.ASSEMBLYAI_BASE_URL.rstrip("/")
    headers = {"authorization": api_key}

    # 1) upload
    upload_url = f"{base}/upload"
    try:
        # AssemblyAI supports chunked upload; do a simple upload
        r = requests.post(
            upload_url, headers=headers, data=audio_bytes, timeout=timeout
        )
        r.raise_for_status()
        uploaded_url = r.json().get("upload_url")
        if not uploaded_url:
            raise TranscriptionError("AssemblyAI upload failed: no upload_url returned")
    except Exception as e:
        logger.exception("AssemblyAI upload failed")
        raise TranscriptionError(str(e))

    # 2) create transcript
    transcript_url = f"{base}/transcript"
    payload = {"audio_url": uploaded_url}
    try:
        r = requests.post(transcript_url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        job = r.json()
        job_id = job.get("id")
        if not job_id:
            raise TranscriptionError("AssemblyAI transcript creation failed")
    except Exception as e:
        logger.exception("AssemblyAI transcript create failed")
        raise TranscriptionError(str(e))

    # 3) poll
    status_url = f"{transcript_url}/{job_id}"
    for _ in range(120):  # up to ~10 minutes depending on poll interval
        try:
            r = requests.get(status_url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            if status == "completed":
                return data.get("text", "")
            if status == "failed":
                raise TranscriptionError(f"Transcription failed: {data.get('error')}")
            time.sleep(2)
        except Exception as e:
            logger.debug("AssemblyAI poll error: %s", e)
            time.sleep(2)
    raise TranscriptionError("Transcription polling timed out")


def transcribe_recording(
    summary_row: Dict[str, Any],
    *,
    assemblyai_api_key: Optional[str] = None,
    transcribe_fn: Optional[Callable[[bytes], str]] = None,
    use_gemini_primary: bool = True,
) -> Dict[str, Any]:
    """
    Attempt to obtain a transcript for a Zoom summary row.

    Priority order:
    1. If an audio-capable file exists:
       a. If transcribe_fn provided: use it
       b. If use_gemini_primary=True: Try Gemini first, then AssemblyAI as fallback
       c. Otherwise: Use AssemblyAI directly
    2. If a transcript file exists in row.recording_files, use it (VTT/TXT cleaning)

    Returns: { "text": str, "source": "gemini"|"assemblyai"|"custom"|"zoom_vtt", "metadata": {...} }
    Raises TranscriptionError if transcription cannot be produced.
    """
    try:
        files = summary_row.get("recording_files") or summary_row.get("files") or []

        # 1) Prefer audio-based transcription when possible
        afile = has_audio_files(files)
        if afile:
            download_url = afile.get("download_url") or afile.get("url")
            if download_url:
                logger.debug(
                    "Found audio file, downloading for transcription: %s", download_url
                )
                audio_bytes = _download_url(download_url)

                # prefer a provided transcribe_fn for testability / custom providers
                if transcribe_fn is not None:
                    text = transcribe_fn(audio_bytes)
                    return {
                        "text": text,
                        "source": "custom_fn",
                        "metadata": {"file": afile.get("file_type")},
                    }

                # Use Gemini as primary with AssemblyAI fallback
                if use_gemini_primary:
                    try:
                        result = transcribe_audio_with_fallback(
                            audio_bytes,
                            assemblyai_api_key=assemblyai_api_key,
                        )
                        result["metadata"]["file"] = afile.get("file_type")
                        return result
                    except TranscriptionError as e:
                        # Log and continue to try Zoom VTT fallback below
                        logger.warning(
                            "Audio transcription via Gemini/AssemblyAI failed; "
                            "will try Zoom transcript if available: %s",
                            e,
                        )

                # Legacy: try AssemblyAI directly if key provided
                api_key = assemblyai_api_key or settings.ASSEMBLYAI_API_KEY
                if api_key:
                    try:
                        text = _transcribe_with_assemblyai_audio_bytes(
                            audio_bytes, api_key
                        )
                        return {
                            "text": text,
                            "source": "assemblyai",
                            "metadata": {"file": afile.get("file_type")},
                        }
                    except TranscriptionError as e:
                        logger.warning(
                            "Audio transcription via AssemblyAI failed; "
                            "will try Zoom transcript if available: %s",
                            e,
                        )

        # 2) Fallback: Zoom native transcript file (if present)
        tfile = has_transcript_file(files)
        if tfile:
            download_url = tfile.get("download_url") or tfile.get("url")
            if download_url:
                logger.debug("Found transcript file, downloading from %s", download_url)
                content_bytes = _download_url(download_url)
                try:
                    text = content_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    text = content_bytes.decode("latin-1", errors="ignore")
                cleaned = clean_vtt_transcript(text)
                if cleaned:
                    return {
                        "text": cleaned,
                        "source": "zoom_vtt",
                        "metadata": {"file": tfile.get("file_type")},
                    }

        # 3) nothing to transcribe
        raise TranscriptionError("No transcript or audio file available on summary row")
    except TranscriptionError:
        raise
    except Exception as e:
        logger.exception("Unexpected transcription error")
        raise TranscriptionError(str(e))
