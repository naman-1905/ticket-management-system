import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import KBArticle
from ..schemas import KBArticleIn, KBArticleOut
from ..deps import require_permissions, current_user
from ..services.tenancy import user_has_permission
from ..utils import err

router = APIRouter()


@router.get("/articles", response_model=list[KBArticleOut])
async def list_articles(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    q = select(KBArticle).where(KBArticle.tenant_id == user.tenant_id)
    if not await user_has_permission(db, user, "kb.manage"):
        q = q.where(KBArticle.visibility == "public", KBArticle.status == "published")
    return (await db.execute(q.order_by(KBArticle.updated_at.desc()))).scalars().all()


@router.post("/articles", response_model=KBArticleOut, status_code=201)
async def create_article(
    body: KBArticleIn,
    user=Depends(require_permissions("kb.manage")),
    db: AsyncSession = Depends(get_db),
):
    article = KBArticle(
        tenant_id=user.tenant_id,
        title=body.title,
        body=body.body,
        visibility=body.visibility,
        status=body.status,
        created_by=user.id,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


@router.get("/articles/{article_id}", response_model=KBArticleOut)
async def get_article(article_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    article = (
        await db.execute(
            select(KBArticle).where(KBArticle.id == article_id, KBArticle.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    if not article:
        err(404, "NOT_FOUND", "Article not found")
    if article.visibility != "public" and not await user_has_permission(db, user, "kb.manage"):
        err(404, "NOT_FOUND", "Article not found")
    return article
