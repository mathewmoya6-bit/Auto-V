from fastapi import APIRouter

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/")
async def list_users():
    return {
        "success": True,
        "message": "Users endpoint working",
        "data": []
    }

@router.get("/{user_id}")
async def get_user(user_id: str):
    return {
        "success": True,
        "user_id": user_id
    }
