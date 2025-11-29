# src/db/mysql_pool.py
import logging
from typing import Optional, Any, List, Tuple
import aiomysql
from aiomysql import OperationalError
from ..config import settings
import time

logger = logging.getLogger(__name__)


class AsyncMySQLPool:
    """
    Production-grade async MySQL pool:
    - Automatic reconnect
    - Connection health checks
    - Idle connection recycling
    - Connection + read timeouts
    """

    _pool: Optional[aiomysql.Pool] = None
    _last_init = 0
    _reinit_interval = 10  # seconds between forced reinit attempts

    @classmethod
    async def init_pool(cls, force=False):
        """Initialize async MySQL connection pool with resilience."""

        # Prevent frequent reinitializations
        now = time.time()
        if cls._pool and not force:
            return

        if not force and now - cls._last_init < cls._reinit_interval:
            return

        cls._last_init = now

        if not settings.MYSQL_USER or not settings.MYSQL_PASSWORD:
            logger.warning("MySQL credentials missing. Skipping pool creation.")
            return

        try:
            cls._pool = await aiomysql.create_pool(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                db=settings.MYSQL_DATABASE,
                minsize=1,
                maxsize=settings.MYSQL_POOL_SIZE,
                autocommit=True,
                charset="utf8mb4",

                # IMPORTANT:
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,

                # Recycle idle connections before MySQL kills them
                pool_recycle=180,     # always < wait_timeout (default 300)
            )
            logger.info("Async MySQL connection pool initialized.")
        except Exception as e:
            logger.exception("Failed to initialize MySQL pool: %s", e)
            cls._pool = None

    @classmethod
    async def get_pool(cls) -> aiomysql.Pool:
        """Get the pool with automatic reconnect on failure."""
        if cls._pool is None:
            await cls.init_pool()

        if cls._pool is None:
            raise RuntimeError("MySQL pool not available")

        return cls._pool

    @classmethod
    async def close_pool(cls):
        if cls._pool:
            try:
                cls._pool.close()
                await cls._pool.wait_closed()
                logger.info("MySQL pool closed.")
            finally:
                cls._pool = None


async def _retry_mysql(op, *args, retries=2, **kwargs):
    """
    Executes a MySQL operation with retry logic for:
    - MySQL server gone away
    - Lost connection
    - Timeout
    """

    for attempt in range(retries):
        try:
            return await op(*args, **kwargs)

        except OperationalError as e:
            err = str(e).lower()
            if "server has gone away" in err or "lost connection" in err or "not connected" in err:
                logger.warning(f"MySQL connection lost. Reconnecting... ({attempt+1}/{retries})")
                await AsyncMySQLPool.init_pool(force=True)
                continue

            raise

        except Exception:
            raise

    raise RuntimeError("MySQL operation failed after retries")


async def execute_query(
    query: str,
    params: Tuple = None,
    fetchone: bool = False,
    fetchall: bool = False,
    log: bool = True
) -> Any:
    """
    Production-safe execution:
    - Retries on connection drop
    - Logs query duration
    """

    async def _execute():
        pool = await AsyncMySQLPool.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                start = time.time()
                await cursor.execute(query, params or ())
                duration = int((time.time() - start) * 1000)

                if log:
                    logger.debug(f"MySQL Query OK ({duration}ms): {query}")

                if fetchone:
                    return await cursor.fetchone()
                if fetchall:
                    return await cursor.fetchall()

                return cursor.rowcount

    return await _retry_mysql(_execute)


async def get_pool() -> aiomysql.Pool:
    """Return pool for advanced usage."""
    return await AsyncMySQLPool.get_pool()
