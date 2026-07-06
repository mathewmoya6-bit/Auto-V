from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from app.schemas import (
    InspectionRequest,
    InspectionResponse,
    InspectionUpdateRequest,
    InspectionReport
)

router = APIRouter()

@router.post("/inspections", response_model=InspectionResponse)
async def create_inspection(request: InspectionRequest):
    """
    Create/schedule a new property inspection
    """
    return InspectionResponse(
        inspection_id="ins_12345",
        property_id=request.property_id,
        inspection_type=request.inspection_type,
        status="scheduled",
        scheduled_date=request.scheduled_date,
        scheduled_time=request.scheduled_time,
        inspector_name=request.inspector_name,
        inspector_company=request.inspector_company,
        client_name=request.client_name,
        client_email=request.client_email,
        created_at=datetime.now(),
        estimated_duration=request.duration_hours or 2.0
    )
