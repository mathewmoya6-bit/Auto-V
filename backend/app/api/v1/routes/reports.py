from fastapi import APIRouter

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)

@router.get("/")
async def reports():
    return {
        "success": True,
        "message": "Reports endpoint working"
    }

@router.get("/{report_id}")
async def get_report(report_id: str):
    return {
        "report_id": report_id
    }
