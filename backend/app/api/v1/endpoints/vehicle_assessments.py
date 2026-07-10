# app/api/v1/endpoints/vehicle_assessments.py
"""
Vehicle Assessments routes.

All routes require auth and should verify the caller owns/can access
`vehicle_id` (same pattern your Vehicles/Inspections modules presumably
already use — swap in your real ownership check).

TODO(integration): adjust imports to your real project layout:
  - app.api.deps.get_db
  - app.api.deps.get_current_user
  - your existing "assert_vehicle_owned_by_user" style dependency/helper
"""
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.vehicle_assessment import (
    AssessmentCreate,
    AssessmentUpdate,
    AssessmentResponse,
    VehicleAssessmentResponse,
    VehicleAssessmentListItem,
    AssessmentHistoryResponse,
    AssessmentStats,
    BulkAssessmentRequest,
    BulkAssessmentResponse,
    AssessmentComparisonRequest,
    AssessmentComparisonResponse,
)
)
from app.services import vehicle_assessment_service as service

# from app.api.deps import get_db, get_current_user

router = APIRouter()


@router.post(
    "/vehicles/{vehicle_id}/assessments",
    response_model=VehicleAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Vehicle Assessments"],
)
async def create_vehicle_assessment(
    vehicle_id: UUID,
    payload: AssessmentCreate = AssessmentCreate(),
    # db=Depends(get_db),
    # current_user=Depends(get_current_user),
):
    """Generate a new composite assessment for a vehicle (inspection + valuation + mileage)."""
    # TODO(integration): verify current_user owns vehicle_id, else 403/404
    return await service.create_assessment(db=None, vehicle_id=vehicle_id, payload=payload)


@router.get(
    "/vehicles/{vehicle_id}/assessments",
    response_model=list[VehicleAssessmentListItem],
    tags=["Vehicle Assessments"],
)
async def get_vehicle_assessments(
    vehicle_id: UUID,
    # db=Depends(get_db),
    # current_user=Depends(get_current_user),
):
    """List all assessments generated for a vehicle, most recent first."""
    return await service.list_assessments(db=None, vehicle_id=vehicle_id)


@router.get(
    "/assessments/{assessment_id}",
    response_model=VehicleAssessmentResponse,
    tags=["Vehicle Assessments"],
)
async def get_assessment(
    assessment_id: UUID,
    # db=Depends(get_db),
    # current_user=Depends(get_current_user),
):
    """Retrieve a single assessment by id."""
    assessment = await service.get_assessment(db=None, assessment_id=assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return assessment


@router.get(
    "/assessments/{assessment_id}/report",
    response_model=VehicleAssessmentReport,
    tags=["Vehicle Assessments"],
)
async def get_assessment_report(
    assessment_id: UUID,
    # db=Depends(get_db),
    # current_user=Depends(get_current_user),
):
    """Return a narrative, export-friendly view of an assessment."""
    assessment = await service.get_assessment(db=None, assessment_id=assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    headline = (
        f"Vehicle scores {assessment.overall_score}/100 "
        f"(Grade {assessment.condition_grade.value})"
    )
    return VehicleAssessmentReport(
        assessment=assessment,
        headline=headline,
        generated_at=datetime.now(timezone.utc),
    )
