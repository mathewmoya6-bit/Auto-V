from fastapi import APIRouter, Request

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)

@router.post("/mpesa")
async def mpesa_webhook(request: Request):
    payload = await request.json()

    return {
        "success": True,
        "received": payload
    }

@router.get("/health")
async def webhook_health():
    return {
        "status": "ok"
    }
