# app/api/v1/endpoints/routes.py
# =============================================================================
# AUTO-V API - Named routes for the "Quick Routes" chips on the frontend
# =============================================================================

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.mileage import Route
from app.schemas.mileage import RouteOut

router = APIRouter()


@router.get("/routes", response_model=List[RouteOut])
async def list_routes(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Route)
        .where(Route.is_active.is_(True))
        .order_by(Route.km)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
