from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from app.core.config import settings
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session: yield session
async def ping_db() -> bool:
    try:
        async with engine.connect() as connection: await connection.execute(text("SELECT 1"))
        return True
    except Exception: return False
