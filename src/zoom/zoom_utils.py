# src/zoom/zoom_utils.py
import re
from typing import List, Dict, Optional

def clean_vtt_transcript(content: str) -> str:
    """Strip WEBVTT cues, timestamps and metadata to plain text."""
    if not content:
        return ""
    lines = content.splitlines()
    text_lines = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("WEBVTT") or ln.startswith("NOTE"):
            continue
        if "-->" in ln:
            continue
        if re.fullmatch(r"\d+", ln):
            continue
        text_lines.append(ln)
    return " ".join(text_lines).strip()

def has_transcript_file(files: List[Dict]) -> Optional[Dict]:
    for f in files or []:
        typ = (f.get("recording_type") or "").lower()
        ext = (f.get("file_type") or "").lower()
        if "transcript" in typ or ext in ("vtt", "txt"):
            return f
    return None

def has_audio_files(files: List[Dict]) -> Optional[Dict]:
    for f in files or []:
        rec_type = (f.get("recording_type") or "").lower()
        ext = (f.get("file_type") or "").lower()
        if rec_type == "audio_only" or ext in ("m4a", "mp3", "wav", "aac", "ogg"):
            return f
    return None
