# src/zoom/zoom_auth.py
"""Zoom OAuth token management with secure persistence."""

from __future__ import annotations
import base64
import json
import logging
import os
from typing import Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from ..config import settings

logger = logging.getLogger(__name__)

# Token file location - use TEMP_DIR from settings for better portability
TOKEN_FILE = Path(settings.TEMP_DIR) / "zoom_tokens.json"


class ZoomTokenManager:
    """Production-safe Zoom OAuth token manager with persistence."""

    def __init__(self):
        self.client_id = settings.ZOOM_CLIENT_ID
        self.client_secret = settings.ZOOM_CLIENT_SECRET

        # Load tokens from file or env
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None

        self._load_tokens()

    # -------------------------------------------------------------
    # Persistent Token Storage
    # -------------------------------------------------------------
    def _load_tokens(self) -> None:
        """Load tokens from file, fallback to env on first run."""
        if TOKEN_FILE.exists():
            try:
                data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))

                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                expires = data.get("expires_at")

                if expires:
                    self.expires_at = datetime.fromisoformat(expires)

                logger.info("Loaded Zoom tokens from disk")
                return
                
            except json.JSONDecodeError as e:
                logger.warning("Token file corrupted, will recreate: %s", e)
            except Exception as e:
                logger.warning("Failed to load token file: %s", e)

        # Fallback to environment on first start
        logger.info("ℹ️ Loading Zoom tokens from environment")
        self.access_token = settings.ZOOM_ACCESS_TOKEN
        self.refresh_token = settings.ZOOM_REFRESH_TOKEN
        self.expires_at = None

        self._save_tokens()  # Save initial state

    def _save_tokens(self) -> None:
        """Persist tokens to local JSON file with secure permissions."""
        try:
            data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            }
            
            # Ensure parent directory exists
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Write atomically to avoid corruption
            temp_file = TOKEN_FILE.with_suffix(".tmp")
            temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temp_file.replace(TOKEN_FILE)
            
            # Set restrictive permissions (owner read/write only)
            try:
                os.chmod(TOKEN_FILE, 0o600)
            except OSError:
                pass  # Windows may not support chmod
            
            logger.info("Zoom tokens saved to disk")
        except Exception as e:
            logger.error("Failed to save zoom token file: %s", e)

    # -------------------------------------------------------------
    # Token Helpers
    # -------------------------------------------------------------
    def _encode_credentials(self) -> str:
        return base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

    def is_valid(self) -> bool:
        """Check if the current access token is valid and not expired."""
        if self.access_token and self.expires_at:
            return datetime.now(timezone.utc) < self.expires_at.replace(tzinfo=timezone.utc)
        return False

    # -------------------------------------------------------------
    # Main Refresh Logic
    # -------------------------------------------------------------
    def refresh(self) -> Optional[str]:
        """Refresh token using Zoom OAuth (persistent)."""
        if not self.refresh_token:
            logger.error("❌ No refresh token available")
            return None

        logger.info("🔄 Refreshing Zoom token...")

        url = "https://zoom.us/oauth/token"
        headers = {
            "Authorization": f"Basic {self._encode_credentials()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        try:
            r = requests.post(url, headers=headers, data=data, timeout=10)
            r.raise_for_status()

            payload = r.json()
            self.access_token = payload.get("access_token")
            new_refresh = payload.get("refresh_token")

            if new_refresh:
                self.refresh_token = new_refresh
                logger.info("🔑 Received new refresh token")

            # Update expiry with safety padding (2 minutes before actual expiry)
            expires = payload.get("expires_in", 3600)
            self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires - 120)

            # Persist to disk
            self._save_tokens()

            logger.info("✅ Zoom token refresh successful")
            return self.access_token

        except Exception as e:
            logger.error(f"❌ Zoom refresh failed: {e}")
            return None
