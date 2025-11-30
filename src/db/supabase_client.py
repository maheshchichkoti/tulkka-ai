"""Supabase client wrapper with production-ready error handling."""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import logging

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from ..config import settings

logger = logging.getLogger(__name__)


class SupabaseClientError(Exception):
    """Custom exception for Supabase operations."""
    pass


class SupabaseClient:
    """
    Production-ready Supabase client wrapper.
    
    Features:
    - Graceful handling of missing credentials
    - Consistent error handling
    - Health check support
    - Type-safe operations
    """

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        self.client: Optional[Client] = None
        self._initialized = False
        
        if not self.url or not self.key:
            logger.warning("Supabase credentials not found. Supabase client disabled.")
            return
        
        try:
            # Configure client with reasonable timeouts when supported.
            # Some supabase-py versions expect different ClientOptions fields
            # (e.g. 'storage'), so we fall back to default options if this fails.
            try:
                options = ClientOptions(
                    postgrest_client_timeout=30,
                    storage_client_timeout=30,
                )
                self.client = create_client(self.url, self.key, options=options)
            except Exception as options_exc:
                logger.warning(
                    "Supabase ClientOptions not supported or incompatible (%s); "
                    "falling back to default client options.",
                    options_exc,
                )
                self.client = create_client(self.url, self.key)

            self._initialized = True
            logger.info("Supabase client initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize Supabase client: %s", e)
            self.client = None
    
    @property
    def is_available(self) -> bool:
        """Check if the client is available for operations."""
        return self._initialized and self.client is not None
    
    def _ensure_client(self) -> Client:
        """Ensure client is available, raise if not."""
        if not self.client:
            raise SupabaseClientError("Supabase client not initialized")
        return self.client

    def health_check(self) -> bool:
        """Check if Supabase connection is healthy."""
        if not self.client:
            return False
        try:
            resp = self.client.table("zoom_summaries").select("id").limit(1).execute()
            # Even empty result is OK - it means connection works
            return True
        except Exception as e:
            logger.warning("Supabase health check failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Insert / Fetch / Update
    # ------------------------------------------------------------------
    def insert_zoom_summary(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert a new zoom summary record."""
        client = self._ensure_client()
        try:
            resp = client.table("zoom_summaries").insert(row).execute()
            data = getattr(resp, "data", []) or []
            return data[0] if data else None
        except Exception as e:
            logger.error("Failed to insert zoom summary: %s", e)
            raise SupabaseClientError(f"Insert failed: {e}") from e

    def fetch_zoom_summary(self, **filters) -> Optional[Dict[str, Any]]:
        """Fetch a zoom summary by filters."""
        client = self._ensure_client()
        try:
            query = client.table("zoom_summaries").select("*")
            for k, v in filters.items():
                if v is not None:  # Skip None values
                    query = query.eq(k, v)
            resp = query.order("created_at", desc=True).limit(1).execute()
            data = getattr(resp, "data", []) or []
            return data[0] if data else None
        except Exception as e:
            logger.error("Failed to fetch zoom summary: %s", e)
            raise SupabaseClientError(f"Fetch failed: {e}") from e

    def update_zoom_summary(self, row_id: Any, payload: Dict[str, Any]) -> bool:
        """Update a zoom summary record."""
        client = self._ensure_client()
        try:
            resp = client.table("zoom_summaries").update(payload).eq("id", row_id).execute()
            return bool(getattr(resp, "data", None))
        except Exception as e:
            logger.error("Failed to update zoom summary %s: %s", row_id, e)
            raise SupabaseClientError(f"Update failed: {e}") from e

    def insert_lesson_exercises(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert lesson exercises."""
        client = self._ensure_client()
        try:
            resp = client.table("lesson_exercises").insert(payload).execute()
            data = getattr(resp, "data", []) or []
            return data[0] if data else None
        except Exception as e:
            logger.error("Failed to insert lesson exercises: %s", e)
            raise SupabaseClientError(f"Insert failed: {e}") from e

    # ------------------------------------------------------------------
    # Task Fetching – PENDING
    # ------------------------------------------------------------------
    def find_pending_summaries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return pending summaries eligible for processing."""
        client = self._ensure_client()
        try:
            resp = (
                client.table("zoom_summaries")
                .select("*")
                .eq("status", "pending")
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            return getattr(resp, "data", []) or []
        except Exception as e:
            logger.error("Failed to find pending summaries: %s", e)
            return []

    def get_zoom_summary_by_id(self, zoom_summary_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific zoom summary by ID."""
        client = self._ensure_client()
        try:
            resp = (
                client.table("zoom_summaries")
                .select("*")
                .eq("id", zoom_summary_id)
                .limit(1)
                .execute()
            )
            data = getattr(resp, "data", []) or []
            return data[0] if data else None
        except Exception as e:
            logger.error("Failed to get zoom summary %s: %s", zoom_summary_id, e)
            raise SupabaseClientError(f"Fetch failed: {e}") from e

    # ------------------------------------------------------------------
    # Reclaim Stale Processing Tasks
    # ------------------------------------------------------------------
    def find_processing_older_than(self, cutoff_unix_timestamp: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Returns tasks that:
          - are still "processing"
          - AND processing_started_at < cutoff timestamp
        Used to recover tasks if the worker crashed and left jobs stuck.
        """
        from datetime import datetime, timezone
        
        client = self._ensure_client()
        try:
            # Convert unix timestamp to ISO8601 because Supabase stores timestamps as text
            cutoff_iso = datetime.fromtimestamp(
                cutoff_unix_timestamp, tz=timezone.utc
            ).isoformat()

            logger.info(
                "Looking for stale processing summaries older than %s (limit=%s)",
                cutoff_iso,
                limit,
            )

            resp = (
                client.table("zoom_summaries")
                .select("*")
                .eq("status", "processing")
                .lt("processing_started_at", cutoff_iso)
                .order("processing_started_at", desc=False)
                .limit(limit)
                .execute()
            )

            return getattr(resp, "data", []) or []

        except Exception as e:
            logger.exception("Failed fetching stale processing rows: %s", e)
            return []
