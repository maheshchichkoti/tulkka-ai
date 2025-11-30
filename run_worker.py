#!/usr/bin/env python3
"""
Improved Worker Entry Point for Processing Zoom Lessons.

Features:
- Graceful shutdown (SIGTERM, SIGINT)
- Automatic restart on crash with exponential backoff
- Heartbeat logs
- Crash-loop protection
- Clean logging with your existing logging_config
"""

import os
import signal
import sys
import time
import logging
import traceback
from typing import List

from src.workers.zoom_processor import run_forever
from src.logging_config import configure_logging

logger = logging.getLogger(__name__)

# Crash loop protection
MAX_CRASHES = 5        # Max crashes allowed in the window
CRASH_WINDOW_SEC = 300  # 5 minutes
crash_times = []


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    sig_name = signal.Signals(signum).name
    logger.info("🛑 Received %s — shutting down worker gracefully...", sig_name)
    sys.exit(0)


def restart_with_backoff(attempt: int):
    """Sleep with exponential backoff."""
    delay = min(30, 2 ** attempt)  # capped at 30s
    logger.warning(f"🔁 Restarting worker in {delay}s (crash attempt #{attempt})...")
    time.sleep(delay)


def record_crash_and_check_limit():
    """Track recent crashes and stop if crash-looping."""
    now = time.time()
    crash_times.append(now)

    # Remove crashes older than the window
    while crash_times and (now - crash_times[0] > CRASH_WINDOW_SEC):
        crash_times.pop(0)

    if len(crash_times) >= MAX_CRASHES:
        logger.critical(
            f"🚨 Worker crash-loop detected ({len(crash_times)} crashes in {CRASH_WINDOW_SEC}s)! "
            "Stopping to avoid infinite restart loop."
        )
        sys.exit(1)


def main_loop():
    """Main supervisor loop."""
    restart_attempt = 0

    while True:
        try:
            logger.info("🚀 Worker started successfully. Processing Zoom tasks...")
            # This never returns unless crashed or exception occurs
            run_forever()

        except SystemExit:
            # Allow graceful exit
            raise

        except Exception as e:
            error = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error(f"💥 Worker crashed unexpectedly:\n{error}")

            record_crash_and_check_limit()
            restart_attempt += 1

            restart_with_backoff(restart_attempt)
            continue  # restart the worker


if __name__ == "__main__":
    # 1. Configure logging
    configure_logging()

    # 2. Register shutdown handlers (Docker/K8s/systemd)
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info("=====================================")
    logger.info("   🚀 Starting Zoom Lesson Worker")
    logger.info("   PID: %s", str(os.getpid()))
    logger.info("=====================================")

    try:
        main_loop()
    except SystemExit:
        logger.info("👋 Worker shut down cleanly.")
    except Exception as e:
        logger.critical("❌ Worker fatal error: %s", e)
        sys.exit(1)
