"""
Pytest configuration for TULKKA Games API tests.
"""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def reset_mysql_pool():
    """Reset MySQL pool before each test to avoid event loop issues."""
    from src.db.mysql_pool import AsyncMySQLPool
    # Close existing pool if any
    if AsyncMySQLPool._pool is not None:
        try:
            AsyncMySQLPool._pool.close()
            await AsyncMySQLPool._pool.wait_closed()
        except Exception:
            pass
        AsyncMySQLPool._pool = None
    yield
    # Cleanup after test
    if AsyncMySQLPool._pool is not None:
        try:
            AsyncMySQLPool._pool.close()
            await AsyncMySQLPool._pool.wait_closed()
        except Exception:
            pass
        AsyncMySQLPool._pool = None
