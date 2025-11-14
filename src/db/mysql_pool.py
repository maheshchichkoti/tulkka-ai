# src/db/mysql_pool.py
import logging
from typing import Optional, Any, List
import aiomysql
from ..config import settings

logger = logging.getLogger(__name__)

class AsyncMySQLPool:
    _pool: Optional[aiomysql.Pool] = None

    @classmethod
    async def init_pool(cls):
        """Initialize async MySQL connection pool"""
        if cls._pool is not None:
            return
        if not settings.MYSQL_USER or not settings.MYSQL_PASSWORD:
            logger.warning("MySQL credentials not provided; skipping pool creation.")
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
                charset='utf8mb4'
            )
            logger.info("Async MySQL connection pool created.")
        except Exception as e:
            logger.exception("Failed creating async MySQL pool: %s", e)
            cls._pool = None

    @classmethod
    async def get_pool(cls) -> aiomysql.Pool:
        """Get the pool, initialize if needed"""
        if cls._pool is None:
            await cls.init_pool()
        if cls._pool is None:
            raise RuntimeError("MySQL pool not available")
        return cls._pool

    @classmethod
    async def close_pool(cls):
        """Close the connection pool"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("MySQL pool closed")

async def execute_query(query: str, params: tuple = None, fetchone: bool = False, fetchall: bool = False) -> Any:
    """Async query execution. Use fetchone=True or fetchall=True to fetch results."""
    pool = await AsyncMySQLPool.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            try:
                await cursor.execute(query, params or ())
                if fetchone:
                    return await cursor.fetchone()
                if fetchall:
                    return await cursor.fetchall()
                await conn.commit()
                return cursor.rowcount
            except Exception as e:
                await conn.rollback()
                logger.exception("MySQL error: %s", e)
                raise

async def get_pool() -> aiomysql.Pool:
    """Return pool for advanced usage"""
    return await AsyncMySQLPool.get_pool()
