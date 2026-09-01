"""Drop and recreate all tables. WARNING: destroys all data."""

import asyncio
import sys

from sqlalchemy import text
from app.db import engine, Base
from app import models  # noqa: F401
from app.services.tenancy import seed_permissions
from sqlalchemy.ext.asyncio import async_sessionmaker


async def main():
    if "--yes" not in sys.argv:
        print("This will DELETE ALL DATA. Re-run with: python -m scripts.reset_db --yes")
        return
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        await seed_permissions(db)
        await db.commit()
    print("Database reset complete.")


if __name__ == "__main__":
    asyncio.run(main())
