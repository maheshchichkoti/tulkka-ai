#!/usr/bin/env python3
"""
Worker entry point for processing Zoom lessons.

Usage:
    python run_worker.py

In Docker:
    CMD ["python", "run_worker.py"]

With process manager (systemd/supervisor):
    ExecStart=/usr/bin/python /app/run_worker.py
"""
import signal
import sys
import logging

from src.workers.zoom_processor import run_forever
from src.logging_config import configure_logging

logger = logging.getLogger(__name__)


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    sig_name = signal.Signals(signum).name
    logger.info("Received %s, shutting down worker gracefully...", sig_name)
    sys.exit(0)


if __name__ == "__main__":
    # Configure logging
    configure_logging()
    
    # Register signal handlers for graceful shutdown (Docker/K8s)
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    logger.info("Starting Zoom lesson processor worker...")
    
    try:
        run_forever()
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt")
    except Exception as e:
        logger.exception("Worker crashed: %s", e)
        sys.exit(1)
