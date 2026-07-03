# app/api/v1/routes/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models import UserProfile

router = APIRouter(prefix="/users", tags=["Users"])


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    company_name: str | None = None
    business_reg: str | None = None
    tax_id: str | None = None


@router.get("/me")
async def get_my_profile(current_user: UserProfile = Depends(get_current_user)):
    return current_user.to_dict()


@router.patch("/me")
async def update_my_profile(
    body: UpdateProfileRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user.to_dict()


@router.get("")
async def list_users(
    _: UserProfile = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: list all users. Pagination intentionally left out
    of this first pass — add limit/offset query params once you know
    expected table size."""
    from sqlalchemy import select

    result = await db.execute(select(UserProfile).order_by(UserProfile.created_at.desc()))
    users = result.scalars().all()
    return [u.to_dict() for u in users]
