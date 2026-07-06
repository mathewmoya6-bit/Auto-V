from fastapi import APIRouter
from typing import List
from datetime import datetime, date
from uuid import UUID
from app.schemas.mileage import (
    CategoryOut,
    VariantOut,
    RouteOut,
    MileageClaimOut,
    MileageClaimCreate,
    MileageClaimUpdate,
    MileageClaimSummary,
    VehicleRateOut,
    MileageApprovalRequest
)

router = APIRouter()

@router.get("/categories", response_model=List[CategoryOut])
async def get_mileage_categories():
    return []

@router.get("/variants", response_model=List[VariantOut])
async def get_mileage_variants():
    return []

@router.get("/routes", response_model=List[RouteOut])
async def get_mileage_routes():
    return []

@router.post("/claims", response_model=MileageClaimOut)
async def create_mileage_claim(claim: MileageClaimCreate):
    return MileageClaimOut(
        id=UUID("12345678-1234-1234-1234-123456789012"),
        user_id=UUID("12345678-1234-1234-1234-123456789012"),
        vehicle_id=None,
        trip_date=claim.trip_date,
        start_location=claim.start_location,
        end_location=claim.end_location,
        distance_km=claim.distance_km,
        vehicle_category=claim.vehicle_category,
        rate_per_km=claim.rate_per_km,
        claim_amount=claim.distance_km * claim.rate_per_km,
        purpose=claim.purpose,
        notes=claim.notes,
        odometer_start=claim.odometer_start,
        odometer_end=claim.odometer_end,
        status="pending",
        approved_by=None,
        approved_at=None,
        created_at=datetime.now()
    )

@router.get("/claims", response_model=List[MileageClaimOut])
async def get_mileage_claims():
    return []

@router.get("/claims/{claim_id}", response_model=MileageClaimOut)
async def get_mileage_claim(claim_id: UUID):
    return MileageClaimOut(
        id=claim_id,
        user_id=UUID("12345678-1234-1234-1234-123456789012"),
        vehicle_id=None,
        trip_date=date.today(),
        start_location="Start",
        end_location="End",
        distance_km=100.0,
        vehicle_category="Sedan",
        rate_per_km=2.50,
        claim_amount=250.0,
        purpose="Business",
        notes="Test claim",
        odometer_start=1000,
        odometer_end=1100,
        status="pending",
        approved_by=None,
        approved_at=None,
        created_at=datetime.now()
    )

@router.patch("/claims/{claim_id}", response_model=MileageClaimOut)
async def update_mileage_claim(claim_id: UUID, update: MileageClaimUpdate):
    return MileageClaimOut(
        id=claim_id,
        user_id=UUID("12345678-1234-1234-1234-123456789012"),
        vehicle_id=None,
        trip_date=date.today(),
        start_location="Start",
        end_location="End",
        distance_km=100.0,
        vehicle_category="Sedan",
        rate_per_km=2.50,
        claim_amount=250.0,
        purpose="Business",
        notes="Updated claim",
        odometer_start=1000,
        odometer_end=1100,
        status="pending",
        approved_by=None,
        approved_at=None,
        created_at=datetime.now()
    )

@router.post("/claims/approve", response_model=MileageClaimOut)
async def approve_mileage_claim(approval: MileageApprovalRequest):
    return MileageClaimOut(
        id=approval.claim_id,
        user_id=UUID("12345678-1234-1234-1234-123456789012"),
        vehicle_id=None,
        trip_date=date.today(),
        start_location="Start",
        end_location="End",
        distance_km=100.0,
        vehicle_category="Sedan",
        rate_per_km=2.50,
        claim_amount=250.0,
        purpose="Business",
        notes="Approved claim",
        odometer_start=1000,
        odometer_end=1100,
        status="approved" if approval.approve else "rejected",
        approved_by=approval.approved_by,
        approved_at=datetime.now(),
        created_at=datetime.now()
    )

@router.get("/claims/summary", response_model=MileageClaimSummary)
async def get_mileage_summary():
    return MileageClaimSummary(
        total_claims=10,
        total_distance_km=1000.0,
        total_claim_amount=2500.0,
        pending_claims=3,
        approved_claims=5,
        rejected_claims=2,
        period_start=date.today().replace(day=1),
        period_end=date.today()
    )

@router.get("/rates", response_model=List[VehicleRateOut])
async def get_vehicle_rates():
    return []
