# src/zoom/zoom_utils.py
import re
from typing import List, Dict, Optional


# -------------------------------------------------------------
# VTT CLEANING (production grade)
# -------------------------------------------------------------
VTT_TIMESTAMP = re.compile(
    r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}"
)
SPEAKER_TAG = re.compile(r"<v[^>]*>")  # <v Speaker 1>, <v->, etc.


def clean_vtt_transcript(content: str) -> str:
    """
    Convert a Zoom VTT transcript into plain text:
    - Remove timestamps
    - Remove <v Speaker> tags
    - Remove WEBVTT metadata
    - Remove cue numbers
    - Collapse whitespace
    """
    if not content:
        return ""

    lines = content.splitlines()
    text_lines = []

    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue

        # Skip headers & metadata
        if ln.startswith("WEBVTT") or ln.startswith("NOTE") or ln.startswith("Kind:") or ln.startswith("Language:"):
            continue

        # Skip cue numbers
        if ln.isdigit():
            continue

        # Skip timestamp lines
        if VTT_TIMESTAMP.search(ln):
            continue

        # Remove <v Speaker> markup
        ln = SPEAKER_TAG.sub("", ln)

        text_lines.append(ln)

    text = " ".join(text_lines)
    # Collapse repeated whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# -------------------------------------------------------------
# TRANSCRIPT FILE DETECTION
# -------------------------------------------------------------
def has_transcript_file(files: List[Dict]) -> Optional[Dict]:
    """Detect transcript-related files from Zoom's recording list."""

    TRANSCRIPT_TYPES = {
        "transcript",
        "closed_caption",
        "cc_transcript",
        "audio_transcript",
        "caption",
    }

    TRANSCRIPT_EXTS = {"vtt", "txt"}

    for f in files or []:
        rec_type = (f.get("recording_type") or "").lower()
        ext = (f.get("file_type") or "").lower()

        if rec_type in TRANSCRIPT_TYPES:
            return f

        if ext in TRANSCRIPT_EXTS:
            return f

    return None


# -------------------------------------------------------------
# AUDIO FILE DETECTION (more robust)
# -------------------------------------------------------------
def has_audio_files(files: List[Dict]) -> Optional[Dict]:
    """
    Detect an audio-capable recording file.
    
    Zoom's audio may be inside:
    - audio_only
    - m4a, mp3, wav, aac, ogg
    - mp4 (video but contains speech track)
    """
    AUDIO_EXTS = {"m4a", "mp3", "wav", "aac", "ogg"}
    VIDEO_WITH_AUDIO_EXTS = {"mp4", "mov", "mkv"}

    for f in files or []:
        rec_type = (f.get("recording_type") or "").lower()
        ext = (f.get("file_type") or "").lower()

        # Strong signal: audio_only file
        if rec_type == "audio_only":
            return f

        # Standard audio formats
        if ext in AUDIO_EXTS:
            return f

        # Video can also contain extractable audio for transcription
        if ext in VIDEO_WITH_AUDIO_EXTS:
            return f

    return None
