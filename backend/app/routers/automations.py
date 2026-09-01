from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import AutomationRule, SavedView, Macro, Tag, TicketTag, Ticket
from ..schemas import AutomationRuleIn, AutomationRuleOut, SavedViewIn, SavedViewOut, MacroIn, MacroOut, TagIn, TagOut
from ..deps import require_permissions, current_user
from ..services.tickets import get_ticket_for_user
import uuid

router = APIRouter()


@router.get("/rules", response_model=list[AutomationRuleOut])
async def list_rules(user=Depends(require_permissions("automation.manage")), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(
            select(AutomationRule).where(AutomationRule.tenant_id == user.tenant_id).order_by(AutomationRule.sort_order)
        )
    ).scalars().all()


@router.post("/rules", response_model=AutomationRuleOut, status_code=201)
async def create_rule(body: AutomationRuleIn, user=Depends(require_permissions("automation.manage")), db: AsyncSession = Depends(get_db)):
    rule = AutomationRule(tenant_id=user.tenant_id, **body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/saved-views", response_model=list[SavedViewOut])
async def list_views(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(
            select(SavedView).where(
                SavedView.tenant_id == user.tenant_id,
                (SavedView.user_id == user.id) | (SavedView.is_shared == True),  # noqa: E712
            )
        )
    ).scalars().all()


@router.post("/saved-views", response_model=SavedViewOut, status_code=201)
async def create_view(body: SavedViewIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    view = SavedView(tenant_id=user.tenant_id, user_id=user.id, **body.model_dump())
    db.add(view)
    await db.commit()
    await db.refresh(view)
    return view


@router.get("/macros", response_model=list[MacroOut])
async def list_macros(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(select(Macro).where(Macro.tenant_id == user.tenant_id, Macro.is_active == True))  # noqa: E712
    ).scalars().all()


@router.post("/macros", response_model=MacroOut, status_code=201)
async def create_macro(body: MacroIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    macro = Macro(tenant_id=user.tenant_id, **body.model_dump())
    db.add(macro)
    await db.commit()
    await db.refresh(macro)
    return macro


@router.get("/tags", response_model=list[TagOut])
async def list_tags(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Tag).where(Tag.tenant_id == user.tenant_id))).scalars().all()


@router.post("/tags", response_model=TagOut, status_code=201)
async def create_tag(body: TagIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tag = Tag(tenant_id=user.tenant_id, name=body.name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.post("/tickets/{ticket_id}/tags/{tag_id}", status_code=204)
async def add_tag(ticket_id: uuid.UUID, tag_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    ticket = await get_ticket_for_user(db, ticket_id, user)
    db.add(TicketTag(ticket_id=ticket.id, tag_id=tag_id))
    await db.commit()
