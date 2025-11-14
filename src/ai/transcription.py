# src/ai/transcription.py
"""
Transcription utilities.

Supports:
- using an uploaded Zoom transcript file (VTT/TXT) if provided
- AssemblyAI (or similar) for audio transcription when AssemblyAI API key is set
- pluggable: callers may pass their own transcribe_fn for custom provider

Functions:
- transcribe_recording(record_row, assemblyai_client=None, transcribe_fn=None)
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

class TranscriptionError(Exception):
    pass

def _download_url(url: str, timeout: int = 120) -> bytes:
    resp = requests.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()
    return resp.content

def _transcribe_with_assemblyai_audio_bytes(audio_bytes: bytes, api_key: str, base_url: str = None, timeout: int = 120) -> str:
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
        r = requests.post(upload_url, headers=headers, data=audio_bytes, timeout=timeout)
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
) -> Dict[str, Any]:
    """
    Attempt to obtain a transcript for a Zoom summary row.
    - If a transcript file exists in row.recording_files, use it (VTT/TXT cleaning).
    - Else if audio file exists and assemblyai_api_key or transcribe_fn provided, use them.
    Returns: { "text": str, "source": "zoom_vtt"|"assemblyai"|"custom", "metadata": {...} }
    Raises TranscriptionError if transcription cannot be produced.
    """
    try:
        files = summary_row.get("recording_files") or summary_row.get("files") or []
        # 1) check for native transcript file
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
                    return {"text": cleaned, "source": "zoom_vtt", "metadata": {"file": tfile.get("file_type")}}
        # 2) fallback: audio file
        afile = has_audio_files(files)
        if afile:
            download_url = afile.get("download_url") or afile.get("url")
            if download_url:
                logger.debug("Found audio file, downloading for transcription: %s", download_url)
                audio_bytes = _download_url(download_url)
                # prefer a provided transcribe_fn for testability / custom providers
                if transcribe_fn is not None:
                    text = transcribe_fn(audio_bytes)
                    return {"text": text, "source": "custom_fn", "metadata": {"file": afile.get("file_type")}}
                # else try AssemblyAI if key provided
                api_key = assemblyai_api_key or settings.ASSEMBLYAI_API_KEY
                if api_key:
                    text = _transcribe_with_assemblyai_audio_bytes(audio_bytes, api_key)
                    return {"text": text, "source": "assemblyai", "metadata": {"file": afile.get("file_type")}}
                raise TranscriptionError("No transcribe function or assemblyai key provided for audio file")
        # 3) nothing to transcribe
        raise TranscriptionError("No transcript or audio file available on summary row")
    except TranscriptionError:
        raise
    except Exception as e:
        logger.exception("Unexpected transcription error")
        raise TranscriptionError(str(e))
