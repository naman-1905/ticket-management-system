import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Project
from ..schemas import ProjectIn, ProjectOut
from ..deps import require_permissions
from ..services.audit import audit_log
from ..utils import err

router = APIRouter()


@router.get("", response_model=list[ProjectOut])
async def list_projects(user=Depends(require_permissions("ticket.view")), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(
            select(Project)
            .where(Project.tenant_id == user.tenant_id, Project.is_active == True)  # noqa: E712
            .order_by(Project.name)
        )
    ).scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectIn,
    user=Depends(require_permissions("ticket.update")),
    db: AsyncSession = Depends(get_db),
):
    exists = (
        await db.execute(select(Project).where(Project.tenant_id == user.tenant_id, Project.name == body.name))
    ).scalar_one_or_none()
    if exists:
        err(409, "CONFLICT", "Project already exists")
    project = Project(tenant_id=user.tenant_id, name=body.name, description=body.description, color=body.color)
    db.add(project)
    await db.flush()
    await audit_log(db, user, "project.created", "project", project.id, new_values={"name": project.name})
    await db.commit()
    await db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectIn,
    user=Depends(require_permissions("ticket.update")),
    db: AsyncSession = Depends(get_db),
):
    project = (
        await db.execute(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    ).scalar_one_or_none()
    if not project:
        err(404, "NOT_FOUND", "Project not found")
    duplicate = (
        await db.execute(
            select(Project).where(
                Project.tenant_id == user.tenant_id, Project.name == body.name, Project.id != project.id
            )
        )
    ).scalar_one_or_none()
    if duplicate:
        err(409, "CONFLICT", "Project already exists")
    project.name = body.name
    project.description = body.description
    project.color = body.color
    await audit_log(db, user, "project.updated", "project", project.id, new_values={"name": project.name})
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    user=Depends(require_permissions("ticket.update")),
    db: AsyncSession = Depends(get_db),
):
    project = (
        await db.execute(select(Project).where(Project.id == project_id, Project.tenant_id == user.tenant_id))
    ).scalar_one_or_none()
    if not project:
        err(404, "NOT_FOUND", "Project not found")
    # tickets.project_id has ON DELETE SET NULL, so existing tickets keep working.
    await audit_log(db, user, "project.deleted", "project", project.id, old_values={"name": project.name})
    await db.delete(project)
    await db.commit()