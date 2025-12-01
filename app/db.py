import asyncpg
from .config import settings
from typing import Any, Dict, List, Optional

_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL, min_size=1, max_size=10)
    return _pool

async def run_query(sql: str, *args) -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *args)
        return [dict(r) for r in rows]

# Small helper for single-row fetch
async def run_query_one(sql: str, *args) -> Dict[str, Any]:
    rows = await run_query(sql, *args)
    return rows[0] if rows else {}
