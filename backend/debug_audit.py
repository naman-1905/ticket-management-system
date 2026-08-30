import asyncio

from sqlalchemy import select
from app.db import SessionLocal
from app.models import AuditLog


async def main():
    async with SessionLocal() as db:
        result = await db.execute(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        )

        rows = result.scalars().all()

        print(f"ROWS: {len(rows)}")

        for i, row in enumerate(rows):
            print("=" * 80)
            print(f"ROW {i}")
            print(f"id          : {row.id}")
            print(f"action      : {row.action}")
            print(f"entity_type : {row.entity_type}")
            print(f"old_values  : {row.old_values!r}")
            print(f"new_values  : {row.new_values!r}")
            print(f"correlation : {row.correlation_id!r}")


asyncio.run(main())