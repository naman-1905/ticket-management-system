import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Team, TeamMember, Queue
from ..schemas import TeamIn, TeamOut, QueueIn, QueueOut
from ..deps import require_permissions
from ..utils import err

router = APIRouter()


@router.get("/teams", response_model=list[TeamOut])
async def list_teams(user=Depends(require_permissions("team.manage")), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(select(Team).where(Team.tenant_id == user.tenant_id).order_by(Team.name))
    ).scalars().all()


@router.post("/teams", response_model=TeamOut, status_code=201)
async def create_team(body: TeamIn, user=Depends(require_permissions("team.manage")), db: AsyncSession = Depends(get_db)):
    team = Team(tenant_id=user.tenant_id, name=body.name)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.post("/teams/{team_id}/members/{user_id}", status_code=204)
async def add_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    user=Depends(require_permissions("team.manage")),
    db: AsyncSession = Depends(get_db),
):
    team = (
        await db.execute(select(Team).where(Team.id == team_id, Team.tenant_id == user.tenant_id))
    ).scalar_one_or_none()
    if not team:
        err(404, "NOT_FOUND", "Team not found")
    db.add(TeamMember(team_id=team.id, user_id=user_id))
    await db.commit()


@router.get("/queues", response_model=list[QueueOut])
async def list_queues(user=Depends(require_permissions("queue.manage")), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(select(Queue).where(Queue.tenant_id == user.tenant_id).order_by(Queue.name))
    ).scalars().all()


@router.post("/queues", response_model=QueueOut, status_code=201)
async def create_queue(body: QueueIn, user=Depends(require_permissions("queue.manage")), db: AsyncSession = Depends(get_db)):
    queue = Queue(
        tenant_id=user.tenant_id,
        name=body.name,
        team_id=body.team_id,
        assignment_mode=body.assignment_mode,
    )
    db.add(queue)
    await db.commit()
    await db.refresh(queue)
    return queue
