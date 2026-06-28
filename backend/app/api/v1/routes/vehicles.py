from fastapi import APIRouter

router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"]
)

@router.get("/")
async def list_vehicles():
    return {
        "success": True,
        "message": "Vehicles endpoint working"
    }

@router.post("/")
async def create_vehicle():
    return {
        "success": True,
        "message": "Vehicle created"
    }
