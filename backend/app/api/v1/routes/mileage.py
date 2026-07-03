from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db

router = APIRouter()

@router.get("/mileage")
async def get_mileage(db: AsyncSession = Depends(get_db)):
    return {"message": "Mileage endpoint - implement me", "data": []}
