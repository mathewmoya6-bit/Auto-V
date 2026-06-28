from fastapi import APIRouter

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)

@router.get("/")
async def list_payments():
    return {
        "success": True
    }

@router.post("/mpesa")
async def mpesa_payment():
    return {
        "success": True,
        "message": "STK Push initiated"
    }
