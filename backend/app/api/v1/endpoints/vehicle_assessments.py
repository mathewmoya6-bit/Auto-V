from uuid import UUID

from fastapi import APIRouter, HTTPException, status

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

from app.services import vehicle_assessment_service as service

router = APIRouter(
    prefix="/vehicle-assessments",
    tags=["Vehicle Assessments"],
)


@router.post(
    "/{vehicle_id}",
    response_model=VehicleAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vehicle_assessment(
    vehicle_id: UUID,
    payload: AssessmentCreate,
):
    """Create a vehicle assessment."""
    return await service.create_assessment(
        vehicle_id=vehicle_id,
        payload=payload,
    )


@router.get(
    "/{vehicle_id}",
    response_model=list[VehicleAssessmentListItem],
)
async def list_vehicle_assessments(
    vehicle_id: UUID,
):
    """List assessments for a vehicle."""
    return await service.list_assessments(
        vehicle_id=vehicle_id,
    )


@router.get(
    "/assessment/{assessment_id}",
    response_model=VehicleAssessmentResponse,
)
async def get_vehicle_assessment(
    assessment_id: UUID,
):
    """Retrieve one assessment."""
    assessment = await service.get_assessment(
        assessment_id=assessment_id,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    return assessment


@router.put(
    "/assessment/{assessment_id}",
    response_model=VehicleAssessmentResponse,
)
async def update_vehicle_assessment(
    assessment_id: UUID,
    payload: AssessmentUpdate,
):
    """Update an assessment."""
    assessment = await service.update_assessment(
        assessment_id=assessment_id,
        payload=payload,
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    return assessment


@router.delete(
    "/assessment/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_vehicle_assessment(
    assessment_id: UUID,
):
    """Delete an assessment."""
    deleted = await service.delete_assessment(
        assessment_id=assessment_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )


@router.post(
    "/bulk",
    response_model=BulkAssessmentResponse,
)
async def bulk_assessment(
    payload: BulkAssessmentRequest,
):
    return await service.bulk_assessment(payload)


@router.post(
    "/compare",
    response_model=AssessmentComparisonResponse,
)
async def compare_assessments(
    payload: AssessmentComparisonRequest,
):
    return await service.compare_assessments(payload)


@router.get(
    "/stats",
    response_model=AssessmentStats,
)
async def assessment_stats():
    return await service.get_stats()
