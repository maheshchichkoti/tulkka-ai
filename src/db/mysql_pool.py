# src/db/mysql_pool.py
import logging
from typing import Optional, Any, List
import mysql.connector
from mysql.connector import pooling, Error as MySQLError
from ..config import settings

logger = logging.getLogger(__name__)

class MysqlPool:
    _pool: Optional[pooling.MySQLConnectionPool] = None

    @classmethod
    def init_pool(cls):
        if cls._pool is not None:
            return
        if not settings.MYSQL_USER or not settings.MYSQL_PASSWORD:
            logger.warning("MySQL credentials not provided; skipping pool creation.")
            return
        try:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name=settings.MYSQL_POOL_NAME,
                pool_size=settings.MYSQL_POOL_SIZE,
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                autocommit=True,
                charset="utf8mb4"
            )
            logger.info("MySQL connection pool created.")
        except MySQLError as e:
            logger.exception("Failed creating MySQL pool: %s", e)
            cls._pool = None

    @classmethod
    def get_conn(cls):
        if cls._pool is None:
            cls.init_pool()
        if cls._pool is None:
            raise RuntimeError("MySQL pool not available")
        return cls._pool.get_connection()

def execute_query(query: str, params: tuple = None, fetchone: bool = False, fetchall: bool = False) -> Any:
    """Sync query execution. Use fetchone=True or fetchall=True to fetch results."""
    conn = MysqlPool.get_conn()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        conn.commit()
        return cursor.rowcount
    except MySQLError as e:
        conn.rollback()
        logger.exception("MySQL error: %s", e)
        raise
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

def get_pool():
    """Return pool for advanced usage"""
    return MysqlPool._pool

# Initialize pool on import attempt (safe)
MysqlPool.init_pool()
