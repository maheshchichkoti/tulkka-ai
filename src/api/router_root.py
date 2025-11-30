"""Root API router with health check endpoints."""

from __future__ import annotations
import logging
from typing import Dict, Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import settings
from ..db.supabase_client import SupabaseClient
from ..time_utils import utc_now_iso

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> Dict[str, Any]:
    """Basic health check - always returns quickly."""
    return {
        "status": "healthy",
        "timestamp": utc_now_iso(),
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/detailed")
async def health_detailed() -> JSONResponse:
    """
    Detailed health check with dependency status.
    
    Returns 200 if core services are healthy, 503 otherwise.
    """
    checks: Dict[str, Dict[str, Any]] = {}
    overall_healthy = True
    
    # Check MySQL
    try:
        from ..db.mysql_pool import AsyncMySQLPool, execute_query
        pool = await AsyncMySQLPool.get_pool()
        if pool:
            await execute_query("SELECT 1", fetchone=True, log=False)
            checks["mysql"] = {"status": "healthy", "connected": True}
        else:
            checks["mysql"] = {"status": "unhealthy", "connected": False, "error": "Pool not initialized"}
            overall_healthy = False
    except Exception as e:
        checks["mysql"] = {"status": "unhealthy", "connected": False, "error": str(e)}
        overall_healthy = False
    
    # Check Supabase
    try:
        supabase = SupabaseClient()
        if supabase.health_check():
            checks["supabase"] = {"status": "healthy", "connected": True}
        else:
            checks["supabase"] = {"status": "unhealthy", "connected": False}
            # Supabase is optional, don't fail overall health
    except Exception as e:
        checks["supabase"] = {"status": "unhealthy", "connected": False, "error": str(e)}
    
    # Check Groq (optional)
    try:
        from ..ai.utils.groq_helper import GroqClient
        groq = GroqClient()
        checks["groq"] = {
            "status": "healthy" if groq.enabled else "disabled",
            "enabled": groq.enabled,
            "model": groq.model if groq.enabled else None
        }
    except Exception as e:
        checks["groq"] = {"status": "error", "error": str(e)}
    
    # Check AssemblyAI (optional)
    try:
        from ..ai.utils.assemblyai_helper import AssemblyAIHelper
        aai = AssemblyAIHelper()
        checks["assemblyai"] = {
            "status": "healthy" if aai.enabled else "disabled",
            "enabled": aai.enabled
        }
    except Exception as e:
        checks["assemblyai"] = {"status": "error", "error": str(e)}
    
    status_code = 200 if overall_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": utc_now_iso(),
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
            "checks": checks
        }
    )


@router.get("/ready")
async def readiness() -> JSONResponse:
    """
    Kubernetes readiness probe.
    
    Returns 200 only if the service can accept traffic.
    """
    try:
        from ..db.mysql_pool import AsyncMySQLPool
        pool = await AsyncMySQLPool.get_pool()
        if pool:
            return JSONResponse(
                status_code=200,
                content={"ready": True, "timestamp": utc_now_iso()}
            )
    except Exception:
        pass
    
    return JSONResponse(
        status_code=503,
        content={"ready": False, "timestamp": utc_now_iso()}
    )
