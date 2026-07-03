from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db

router = APIRouter()

@router.get("/fleet")
async def get_fleet(db: AsyncSession = Depends(get_db)):
    return {"message": "Fleet endpoint - implement me", "data": []}
