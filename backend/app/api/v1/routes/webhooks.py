from fastapi import APIRouter, Request

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"]
)

@router.post("/mpesa")
async def mpesa_webhook(request: Request):
    body = await request.json()

    return {
        "received": True,
        "payload": body
    }
