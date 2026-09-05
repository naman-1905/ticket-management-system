"""Create all tables and seed permissions. Run: python -m scripts.bootstrap_db"""

import asyncio

from app.db import engine, Base
from app import models  # noqa: F401
from app.services.tenancy import seed_permissions
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all only adds missing tables; add any new columns to existing tables here.
        await conn.execute(
            text(
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS project_id UUID "
                "REFERENCES projects(id) ON DELETE SET NULL"
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tickets_project_id ON tickets(project_id)"))
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        await seed_permissions(db)
        await db.commit()
    print("Database schema ready.")


if __name__ == "__main__":
    asyncio.run(main())
