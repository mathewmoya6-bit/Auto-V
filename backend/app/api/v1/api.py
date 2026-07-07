# app/api/v1/api.py
from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.mileage import router as mileage_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(mileage_router, prefix="/mileage", tags=["Mileage"])

@api_router.get("/ping")
async def ping():
    return {"status": "ok", "message": "API is running", "version": "3.1.0"}
