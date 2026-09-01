"""Create all tables and seed permissions. Run: python -m scripts.bootstrap_db"""

import asyncio

from app.db import engine, Base
from app import models  # noqa: F401
from app.services.tenancy import seed_permissions
from sqlalchemy.ext.asyncio import async_sessionmaker


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        await seed_permissions(db)
        await db.commit()
    print("Database schema ready.")


if __name__ == "__main__":
    asyncio.run(main())
