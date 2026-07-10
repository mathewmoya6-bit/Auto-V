# app/api/v1/routes/vehicles.py
# =============================================================================
# AUTO-V API - Vehicle Routes
# =============================================================================
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user, get_current_admin_user
from app.schemas.user import UserProfile
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate, VehicleDetailResponse
from app.services.vehicle_service import VehicleService

router = APIRouter(tags=["Vehicles"])


def get_vehicle_service() -> VehicleService:
    return VehicleService()


# =============================================================================
# PUBLIC REFERENCE DATA — no auth required.
#
# IMPORTANT: this must be declared BEFORE the /{vehicle_id} route below.
# FastAPI/Starlette matches routes in registration order, and "/models" would
# otherwise be swallowed by "/{vehicle_id}" (treating "models" as a UUID),
# which is exactly what was causing the 401 — it was hitting the
# authenticated single-vehicle lookup instead of a real "list models" route.
# =============================================================================

class VehicleModelEntry(BaseModel):
    make: str
    model: str


# Static reference list for now. Swap the body of list_vehicle_models() for a
# Supabase table lookup (e.g. a `vehicle_makes` / `vehicle_models` table) once
# one exists — the response shape here is designed to match that migration
# path with no frontend changes needed.
_VEHICLE_MODEL_CATALOG: List[VehicleModelEntry] = [
    VehicleModelEntry(make="Toyota", model="Corolla"),
    VehicleModelEntry(make="Toyota", model="Axio"),
    VehicleModelEntry(make="Toyota", model="Camry"),
    VehicleModelEntry(make="Toyota", model="RAV4"),
    VehicleModelEntry(make="Toyota", model="Hilux"),
    VehicleModelEntry(make="Toyota", model="Land Cruiser"),
    VehicleModelEntry(make="Honda", model="Civic"),
    VehicleModelEntry(make="Honda", model="Accord"),
    VehicleModelEntry(make="Honda", model="CR-V"),
    VehicleModelEntry(make="Honda", model="Fit"),
    VehicleModelEntry(make="Nissan", model="X-Trail"),
    VehicleModelEntry(make="Nissan", model="Patrol"),
    VehicleModelEntry(make="Nissan", model="Note"),
    VehicleModelEntry(make="Nissan", model="Qashqai"),
    VehicleModelEntry(make="BMW", model="X5"),
    VehicleModelEntry(make="BMW", model="3 Series"),
    VehicleModelEntry(make="BMW", model="5 Series"),
    VehicleModelEntry(make="BMW", model="7 Series"),
    VehicleModelEntry(make="Mercedes", model="C-Class"),
    VehicleModelEntry(make="Mercedes", model="E-Class"),
    VehicleModelEntry(make="Mercedes", model="GLC"),
    VehicleModelEntry(make="Mercedes", model="GLE"),
]


# ─── Public Endpoints (No Auth Required) ────────────────────────────

@router.get("/models", response_model=List[VehicleModelEntry])
async def list_vehicle_models():
    """
    Public catalog of make/model combinations, used to populate dropdowns
    (e.g. instant-value.html). Deliberately has NO auth dependency — this
    is reference data, not user data.
    """
    return _VEHICLE_MODEL_CATALOG


@router.get("/makes", response_model=List[str])
async def list_vehicle_makes():
    """
    Get unique list of vehicle makes.
    Used for dropdown population.
    """
    makes = sorted(set(item.make for item in _VEHICLE_MODEL_CATALOG))
    return makes


@router.get("/models/{make}", response_model=List[str])
async def get_models_by_make(make: str):
    """
    Get models for a specific make.
    """
    models = sorted(set(
        item.model for item in _VEHICLE_MODEL_CATALOG 
        if item.make.lower() == make.lower()
    ))
    if not models:
        raise HTTPException(status_code=404, detail=f"No models found for make: {make}")
    return models


# ─── Authenticated User-Vehicle CRUD ────────────────────────────────

@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Create a new vehicle for the current user"""
    return await service.create_vehicle(UUID(current_user.id), payload)


@router.get("/", response_model=List[VehicleResponse])
async def list_vehicles(
    current_user: UserProfile = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status (active, sold, etc.)"),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Get all vehicles for the current user"""
    return await service.list_vehicles(UUID(current_user.id), status)


@router.get("/{vehicle_id}", response_model=VehicleDetailResponse)
async def get_vehicle(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Get a specific vehicle by ID with full details"""
    is_admin = current_user.role == "admin"
    return await service.get_vehicle(vehicle_id, UUID(current_user.id), is_admin)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdate,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Update a vehicle's details"""
    is_admin = current_user.role == "admin"
    return await service.update_vehicle(vehicle_id, UUID(current_user.id), payload, is_admin)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Delete a vehicle"""
    is_admin = current_user.role == "admin"
    await service.delete_vehicle(vehicle_id, UUID(current_user.id), is_admin)


# ─── Vehicle Search & Filter ─────────────────────────────────────────

@router.get("/search", response_model=List[VehicleResponse])
async def search_vehicles(
    current_user: UserProfile = Depends(get_current_user),
    make: Optional[str] = Query(None, description="Filter by make"),
    model: Optional[str] = Query(None, description="Filter by model"),
    year_from: Optional[int] = Query(None, description="Minimum year"),
    year_to: Optional[int] = Query(None, description="Maximum year"),
    status: Optional[str] = Query(None, description="Filter by status"),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Search vehicles with filters"""
    return await service.search_vehicles(
        UUID(current_user.id),
        make=make,
        model=model,
        year_from=year_from,
        year_to=year_to,
        status=status
    )


@router.get("/count", response_model=dict)
async def get_vehicle_count(
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Get count of user's vehicles"""
    count = await service.get_vehicle_count(UUID(current_user.id))
    return {"total": count}


# ─── Admin Endpoints ──────────────────────────────────────────────────

@router.get("/admin/all", response_model=List[VehicleResponse])
async def admin_list_all_vehicles(
    current_admin: UserProfile = Depends(get_current_admin_user),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: VehicleService = Depends(get_vehicle_service),
):
    """List all vehicles across all users (Admin only)"""
    return await service.admin_list_all_vehicles(limit, offset)


@router.get("/admin/stats", response_model=dict)
async def admin_get_vehicle_stats(
    current_admin: UserProfile = Depends(get_current_admin_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Get global vehicle statistics (Admin only)"""
    return await service.admin_get_vehicle_stats()


# ─── Bulk Operations ──────────────────────────────────────────────────

@router.post("/bulk", response_model=List[VehicleResponse], status_code=status.HTTP_201_CREATED)
async def create_vehicles_bulk(
    payloads: List[VehicleCreate],
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Create multiple vehicles at once"""
    return await service.create_vehicles_bulk(UUID(current_user.id), payloads)


@router.patch("/bulk/status", response_model=dict)
async def bulk_update_status(
    vehicle_ids: List[UUID],
    status: str,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Bulk update vehicle status"""
    is_admin = current_user.role == "admin"
    updated = await service.bulk_update_status(vehicle_ids, UUID(current_user.id), status, is_admin)
    return {"updated": updated}


# ─── Vehicle Export ──────────────────────────────────────────────────

@router.get("/export/csv")
async def export_vehicles_csv(
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    """Export user's vehicles to CSV format"""
    return await service.export_vehicles_csv(UUID(current_user.id))
