import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..config import settings
from ..db import engine
from ..models import WorkerHeartbeat, Job
from ..services.sla import process_sla_breaches

logger = logging.getLogger(__name__)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
WORKER_ID = str(uuid.uuid4())


async def heartbeat(db: AsyncSession):
    row = (
        await db.execute(select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == WORKER_ID))
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row:
        row.last_seen_at = now
    else:
        db.add(WorkerHeartbeat(worker_id=WORKER_ID, last_seen_at=now))


async def process_jobs(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    jobs = (
        await db.execute(
            select(Job)
            .where(Job.status == "pending", Job.run_at <= now)
            .order_by(Job.run_at)
            .limit(20)
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()
    count = 0
    for job in jobs:
        job.status = "running"
        job.attempts += 1
        try:
            if job.job_type == "sla_check":
                await process_sla_breaches(db)
            job.status = "completed"
            count += 1
        except Exception as exc:
            job.last_error = str(exc)
            if job.attempts >= job.max_attempts:
                job.status = "failed"
            else:
                job.status = "pending"
            logger.exception("Job %s failed", job.id)
    return count


async def run_once():
    async with SessionLocal() as db:
        await heartbeat(db)
        await process_sla_breaches(db)
        await process_jobs(db)
        await db.commit()


async def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Worker %s started", WORKER_ID)
    while True:
        try:
            await run_once()
        except Exception:
            logger.exception("Worker loop error")
        await asyncio.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(main())
