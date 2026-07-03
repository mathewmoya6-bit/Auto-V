from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db

router = APIRouter()

@router.get("/admin")
async def admin_dashboard(db: AsyncSession = Depends(get_db)):
    return {"message": "Admin endpoint - implement me"}
