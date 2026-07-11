# app/api/v1/routes/vehicles.py
# =============================================================================
# AUTO-V API - Vehicle Routes
# =============================================================================
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.schemas.user import UserProfile
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


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
#
# NOTE: the `make` values here must match the <option value="..."> values
# in instant-value.html's #make dropdown EXACTLY (including suffixes like
# "Suzuki Car" vs "Suzuki Bike", "BMW" vs "BMW Motorrad") — the frontend
# keys its MODEL_MAP off this exact string.
_VEHICLE_MODEL_CATALOG: List[VehicleModelEntry] = [
    # ─── Cars ───────────────────────────────────────────────────────
    VehicleModelEntry(make="Toyota", model="Corolla"),
    VehicleModelEntry(make="Toyota", model="Axio"),
    VehicleModelEntry(make="Toyota", model="Camry"),
    VehicleModelEntry(make="Toyota", model="RAV4"),
    VehicleModelEntry(make="Toyota", model="Hilux"),
    VehicleModelEntry(make="Toyota", model="Land Cruiser"),
    VehicleModelEntry(make="Toyota", model="Prado"),
    VehicleModelEntry(make="Toyota", model="Vitz"),
    VehicleModelEntry(make="Toyota", model="Harrier"),
    VehicleModelEntry(make="Toyota", model="Fielder"),
    VehicleModelEntry(make="Nissan", model="X-Trail"),
    VehicleModelEntry(make="Nissan", model="Patrol"),
    VehicleModelEntry(make="Nissan", model="Note"),
    VehicleModelEntry(make="Nissan", model="Qashqai"),
    VehicleModelEntry(make="Nissan", model="Navara"),
    VehicleModelEntry(make="Nissan", model="Juke"),
    VehicleModelEntry(make="BMW", model="X5"),
    VehicleModelEntry(make="BMW", model="3 Series"),
    VehicleModelEntry(make="BMW", model="5 Series"),
    VehicleModelEntry(make="BMW", model="7 Series"),
    VehicleModelEntry(make="BMW", model="X3"),
    VehicleModelEntry(make="Mercedes", model="C-Class"),
    VehicleModelEntry(make="Mercedes", model="E-Class"),
    VehicleModelEntry(make="Mercedes", model="GLC"),
    VehicleModelEntry(make="Mercedes", model="GLE"),
    VehicleModelEntry(make="Mercedes", model="S-Class"),
    VehicleModelEntry(make="Honda", model="Civic"),
    VehicleModelEntry(make="Honda", model="Accord"),
    VehicleModelEntry(make="Honda", model="CR-V"),
    VehicleModelEntry(make="Honda", model="Fit"),
    VehicleModelEntry(make="Honda", model="Vezel"),
    VehicleModelEntry(make="Mazda", model="Demio"),
    VehicleModelEntry(make="Mazda", model="Axela"),
    VehicleModelEntry(make="Mazda", model="CX-5"),
    VehicleModelEntry(make="Mazda", model="CX-3"),
    VehicleModelEntry(make="Mazda", model="Atenza"),
    VehicleModelEntry(make="Volkswagen", model="Golf"),
    VehicleModelEntry(make="Volkswagen", model="Passat"),
    VehicleModelEntry(make="Volkswagen", model="Tiguan"),
    VehicleModelEntry(make="Volkswagen", model="Polo"),
    VehicleModelEntry(make="Mitsubishi", model="Pajero"),
    VehicleModelEntry(make="Mitsubishi", model="Outlander"),
    VehicleModelEntry(make="Mitsubishi", model="Lancer"),
    VehicleModelEntry(make="Mitsubishi", model="ASX"),
    VehicleModelEntry(make="Subaru", model="Forester"),
    VehicleModelEntry(make="Subaru", model="Outback"),
    VehicleModelEntry(make="Subaru", model="Impreza"),
    VehicleModelEntry(make="Subaru", model="Legacy"),
    VehicleModelEntry(make="Ford", model="Ranger"),
    VehicleModelEntry(make="Ford", model="Escape"),
    VehicleModelEntry(make="Ford", model="Everest"),
    VehicleModelEntry(make="Ford", model="Focus"),
    VehicleModelEntry(make="Chevrolet", model="Spark"),
    VehicleModelEntry(make="Chevrolet", model="Trailblazer"),
    VehicleModelEntry(make="Chevrolet", model="Cruze"),
    VehicleModelEntry(make="Jeep", model="Wrangler"),
    VehicleModelEntry(make="Jeep", model="Grand Cherokee"),
    VehicleModelEntry(make="Jeep", model="Compass"),
    VehicleModelEntry(make="Land Rover", model="Discovery"),
    VehicleModelEntry(make="Land Rover", model="Range Rover"),
    VehicleModelEntry(make="Land Rover", model="Defender"),
    VehicleModelEntry(make="Land Rover", model="Evoque"),
    VehicleModelEntry(make="Hyundai", model="Tucson"),
    VehicleModelEntry(make="Hyundai", model="Elantra"),
    VehicleModelEntry(make="Hyundai", model="Santa Fe"),
    VehicleModelEntry(make="Hyundai", model="i10"),
    VehicleModelEntry(make="Kia", model="Sportage"),
    VehicleModelEntry(make="Kia", model="Sorento"),
    VehicleModelEntry(make="Kia", model="Rio"),
    VehicleModelEntry(make="Kia", model="Picanto"),
    VehicleModelEntry(make="Peugeot", model="308"),
    VehicleModelEntry(make="Peugeot", model="3008"),
    VehicleModelEntry(make="Peugeot", model="508"),
    VehicleModelEntry(make="Suzuki Car", model="Swift"),
    VehicleModelEntry(make="Suzuki Car", model="Vitara"),
    VehicleModelEntry(make="Suzuki Car", model="Alto"),
    VehicleModelEntry(make="Suzuki Car", model="Jimny"),
    VehicleModelEntry(make="Isuzu", model="D-Max"),
    VehicleModelEntry(make="Isuzu", model="MU-X"),
    VehicleModelEntry(make="Isuzu", model="NPR"),
    VehicleModelEntry(make="Daihatsu", model="Terios"),
    VehicleModelEntry(make="Daihatsu", model="Mira"),
    VehicleModelEntry(make="Daihatsu", model="Hijet"),
    # ─── Bikes ──────────────────────────────────────────────────────
    VehicleModelEntry(make="Honda Bike", model="CB150"),
    VehicleModelEntry(make="Honda Bike", model="CRF250"),
    VehicleModelEntry(make="Honda Bike", model="CG125"),
    VehicleModelEntry(make="Honda Bike", model="Africa Twin"),
    VehicleModelEntry(make="Yamaha", model="YBR125"),
    VehicleModelEntry(make="Yamaha", model="MT-07"),
    VehicleModelEntry(make="Yamaha", model="R15"),
    VehicleModelEntry(make="Yamaha", model="DT125"),
    VehicleModelEntry(make="Suzuki Bike", model="GN125"),
    VehicleModelEntry(make="Suzuki Bike", model="GSX-R150"),
    VehicleModelEntry(make="Suzuki Bike", model="Gixxer"),
    VehicleModelEntry(make="Kawasaki", model="KLX150"),
    VehicleModelEntry(make="Kawasaki", model="Ninja 250"),
    VehicleModelEntry(make="Kawasaki", model="Versys"),
    VehicleModelEntry(make="TVS", model="Star HLX"),
    VehicleModelEntry(make="TVS", model="Apache"),
    VehicleModelEntry(make="TVS", model="Raider"),
    VehicleModelEntry(make="Bajaj", model="Boxer"),
    VehicleModelEntry(make="Bajaj", model="Pulsar"),
    VehicleModelEntry(make="Bajaj", model="CT100"),
    VehicleModelEntry(make="Hero", model="Splendor"),
    VehicleModelEntry(make="Hero", model="Hunk"),
    VehicleModelEntry(make="Hero", model="Glamour"),
    VehicleModelEntry(make="Royal Enfield", model="Classic 350"),
    VehicleModelEntry(make="Royal Enfield", model="Himalayan"),
    VehicleModelEntry(make="Royal Enfield", model="Bullet"),
    VehicleModelEntry(make="KTM", model="Duke 200"),
    VehicleModelEntry(make="KTM", model="Adventure 390"),
    VehicleModelEntry(make="Aprilia", model="RS 660"),
    VehicleModelEntry(make="Aprilia", model="Tuono"),
    VehicleModelEntry(make="BMW Motorrad", model="F850GS"),
    VehicleModelEntry(make="BMW Motorrad", model="R1250GS"),
    VehicleModelEntry(make="Ducati", model="Monster"),
    VehicleModelEntry(make="Ducati", model="Panigale"),
    VehicleModelEntry(make="Triumph", model="Street Triple"),
    VehicleModelEntry(make="Triumph", model="Tiger"),
    VehicleModelEntry(make="Harley Davidson", model="Iron 883"),
    VehicleModelEntry(make="Harley Davidson", model="Street Bob"),
    VehicleModelEntry(make="MV Agusta", model="Brutale"),
    VehicleModelEntry(make="MV Agusta", model="F3"),
    # ─── Tricycles ──────────────────────────────────────────────────
    VehicleModelEntry(make="Piaggio", model="Ape"),
    VehicleModelEntry(make="Piaggio", model="Ape City"),
    VehicleModelEntry(make="TVS Tricycle", model="King"),
    VehicleModelEntry(make="TVS Tricycle", model="King Deluxe"),
    VehicleModelEntry(make="Bajaj Tricycle", model="RE"),
    VehicleModelEntry(make="Bajaj Tricycle", model="Maxima"),
]


@router.get("/models", response_model=List[VehicleModelEntry])
async def list_vehicle_models():
    """
    Public catalog of make/model combinations, used to populate dropdowns
    (e.g. instant-value.html). Deliberately has NO auth dependency — this
    is reference data, not user data.
    """
    return _VEHICLE_MODEL_CATALOG


# =============================================================================
# AUTHENTICATED USER-VEHICLE CRUD (unchanged from before)
# =============================================================================

@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    return await service.create_vehicle(UUID(current_user.id), payload)


@router.get("/", response_model=List[VehicleResponse])
async def list_vehicles(
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    return await service.list_vehicles(UUID(current_user.id))


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    is_admin = current_user.role == "admin"
    return await service.get_vehicle(vehicle_id, UUID(current_user.id), is_admin)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdate,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    is_admin = current_user.role == "admin"
    return await service.update_vehicle(vehicle_id, UUID(current_user.id), payload, is_admin)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    service: VehicleService = Depends(get_vehicle_service),
):
    is_admin = current_user.role == "admin"
    await service.delete_vehicle(vehicle_id, UUID(current_user.id), is_admin)
