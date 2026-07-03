# app/api/v1/routes/mileage.py
# =============================================================================
# AUTO-V API - Mileage Routes (Public)
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mileage", tags=["Mileage"])


# ─── Response Models ──────────────────────────────────────────────
class ComponentCost(BaseModel):
    insurance: float = 0
    depreciation: float = 0
    interest: float = 0
    fuel: float = 0
    servicing: float = 0
    repairs: float = 0
    tyres: float = 0
    licences: float = 0


class VariantResponse(BaseModel):
    id: str
    label: str
    category_id: str
    category_name: str
    fixed_per_km: float = 0
    operating_per_km: float = 0
    total_per_km: float = 0
    initial_cost: float = 0
    year1: float = 0
    year2: float = 0
    year3: float = 0
    year4: float = 0
    year5: float = 0
    components: ComponentCost = Field(default_factory=ComponentCost)


class CategoryResponse(BaseModel):
    id: str
    label: str
    fuel_type: str = "—"
    variants: List[VariantResponse] = []


class RouteResponse(BaseModel):
    from_city: str
    to_city: str
    km: float


# ─── MOCK DATA ──────────────────────────────────────────────────────
MOCK_CATEGORIES = [
    {
        "id": "cat-1",
        "label": "Toyota Axio (1500cc)",
        "fuel_type": "Petrol",
        "variants": [
            {
                "id": "var-1",
                "label": "Axio X (2018-2022)",
                "fixed_per_km": 12.50,
                "operating_per_km": 18.75,
                "total_per_km": 31.25,
                "initial_cost": 2850000,
                "year1": 31.25,
                "year2": 34.50,
                "year3": 38.75,
                "year4": 43.00,
                "year5": 48.50,
                "components": {
                    "insurance": 3.50,
                    "depreciation": 5.00,
                    "interest": 2.00,
                    "fuel": 9.75,
                    "servicing": 2.50,
                    "repairs": 3.50,
                    "tyres": 2.00,
                    "licences": 2.00
                }
            },
            {
                "id": "var-2",
                "label": "Axio G (2018-2022)",
                "fixed_per_km": 13.75,
                "operating_per_km": 19.50,
                "total_per_km": 33.25,
                "initial_cost": 3200000,
                "year1": 33.25,
                "year2": 36.50,
                "year3": 40.75,
                "year4": 45.00,
                "year5": 50.50,
                "components": {
                    "insurance": 4.00,
                    "depreciation": 5.50,
                    "interest": 2.25,
                    "fuel": 10.00,
                    "servicing": 2.75,
                    "repairs": 3.75,
                    "tyres": 2.25,
                    "licences": 2.00
                }
            }
        ]
    },
    {
        "id": "cat-2",
        "label": "Toyota Land Cruiser Prado",
        "fuel_type": "Diesel",
        "variants": [
            {
                "id": "var-3",
                "label": "Prado TX (2015-2020)",
                "fixed_per_km": 28.00,
                "operating_per_km": 35.00,
                "total_per_km": 63.00,
                "initial_cost": 6000000,
                "year1": 63.00,
                "year2": 68.00,
                "year3": 74.00,
                "year4": 81.00,
                "year5": 89.00,
                "components": {
                    "insurance": 12.00,
                    "depreciation": 10.00,
                    "interest": 6.00,
                    "fuel": 18.00,
                    "servicing": 5.00,
                    "repairs": 6.00,
                    "tyres": 3.00,
                    "licences": 3.00
                }
            }
        ]
    },
    {
        "id": "cat-3",
        "label": "Toyota Hilux Double Cab",
        "fuel_type": "Diesel",
        "variants": [
            {
                "id": "var-4",
                "label": "Hilux 2.8 GD-6 (2016-2022)",
                "fixed_per_km": 22.50,
                "operating_per_km": 28.00,
                "total_per_km": 50.50,
                "initial_cost": 4800000,
                "year1": 50.50,
                "year2": 54.50,
                "year3": 59.50,
                "year4": 65.50,
                "year5": 72.50,
                "components": {
                    "insurance": 8.00,
                    "depreciation": 8.00,
                    "interest": 4.50,
                    "fuel": 14.50,
                    "servicing": 4.50,
                    "repairs": 5.00,
                    "tyres": 2.50,
                    "licences": 2.50
                }
            }
        ]
    },
    {
        "id": "cat-4",
        "label": "Honda Fit (1300cc)",
        "fuel_type": "Petrol",
        "variants": [
            {
                "id": "var-5",
                "label": "Fit 1.3 (2015-2020)",
                "fixed_per_km": 10.50,
                "operating_per_km": 16.25,
                "total_per_km": 26.75,
                "initial_cost": 1800000,
                "year1": 26.75,
                "year2": 29.50,
                "year3": 33.25,
                "year4": 37.50,
                "year5": 42.75,
                "components": {
                    "insurance": 3.00,
                    "depreciation": 4.00,
                    "interest": 1.50,
                    "fuel": 8.25,
                    "servicing": 2.00,
                    "repairs": 3.00,
                    "tyres": 1.75,
                    "licences": 1.75
                }
            }
        ]
    },
    {
        "id": "cat-5",
        "label": "Mercedes-Benz E-Class",
        "fuel_type": "Petrol",
        "variants": [
            {
                "id": "var-6",
                "label": "E 300 (2016-2022)",
                "fixed_per_km": 35.00,
                "operating_per_km": 40.00,
                "total_per_km": 75.00,
                "initial_cost": 8500000,
                "year1": 75.00,
                "year2": 82.00,
                "year3": 90.00,
                "year4": 99.00,
                "year5": 110.00,
                "components": {
                    "insurance": 15.00,
                    "depreciation": 12.00,
                    "interest": 8.00,
                    "fuel": 20.00,
                    "servicing": 6.00,
                    "repairs": 7.00,
                    "tyres": 4.00,
                    "licences": 3.00
                }
            }
        ]
    },
    {
        "id": "cat-6",
        "label": "Toyota Hiace (14 Seater)",
        "fuel_type": "Diesel",
        "variants": [
            {
                "id": "var-7",
                "label": "Hiace Commuter (2015-2022)",
                "fixed_per_km": 25.00,
                "operating_per_km": 32.00,
                "total_per_km": 57.00,
                "initial_cost": 3500000,
                "year1": 57.00,
                "year2": 62.00,
                "year3": 68.00,
                "year4": 75.00,
                "year5": 83.00,
                "components": {
                    "insurance": 10.00,
                    "depreciation": 8.00,
                    "interest": 4.00,
                    "fuel": 16.00,
                    "servicing": 4.00,
                    "repairs": 5.00,
                    "tyres": 3.00,
                    "licences": 2.00
                }
            }
        ]
    }
]

MOCK_ROUTES = [
    {"from_city": "Nairobi", "to_city": "Mombasa", "km": 485},
    {"from_city": "Nairobi", "to_city": "Kisumu", "km": 355},
    {"from_city": "Nairobi", "to_city": "Nakuru", "km": 155},
    {"from_city": "Nairobi", "to_city": "Eldoret", "km": 310},
    {"from_city": "Nairobi", "to_city": "Thika", "km": 42},
    {"from_city": "Nairobi", "to_city": "Malindi", "km": 520},
    {"from_city": "Mombasa", "to_city": "Malindi", "km": 120},
    {"from_city": "Nairobi", "to_city": "Meru", "km": 270},
    {"from_city": "Nairobi", "to_city": "Nyeri", "km": 150},
    {"from_city": "Kisumu", "to_city": "Eldoret", "km": 120},
]


# ─── PUBLIC API ENDPOINTS (No Authentication Required) ────────────

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories():
    """
    Get all vehicle categories with their variants.
    This endpoint is PUBLIC - no authentication required.
    """
    return MOCK_CATEGORIES


@router.get("/routes", response_model=List[RouteResponse])
async def get_routes():
    """
    Get all quick routes with distances.
    This endpoint is PUBLIC - no authentication required.
    """
    return MOCK_ROUTES


@router.get("/rates")
async def get_mileage_rates():
    """Get all mileage rates (flattened view)."""
    rates = []
    for cat in MOCK_CATEGORIES:
        for variant in cat["variants"]:
            rates.append({
                "category": cat["label"],
                "variant": variant["label"],
                "rate_per_km": variant["total_per_km"],
                "fixed_per_km": variant["fixed_per_km"],
                "operating_per_km": variant["operating_per_km"],
                "fuel_type": cat["fuel_type"],
            })
    return rates


@router.get("/calculate")
async def calculate_mileage(
    category_id: str,
    variant_id: str,
    distance_km: float,
):
    """Calculate mileage cost for a specific vehicle and distance."""
    variant = None
    category = None
    
    for cat in MOCK_CATEGORIES:
        if cat["id"] == category_id:
            category = cat
            for v in cat["variants"]:
                if v["id"] == variant_id:
                    variant = v
                    break
            break
    
    if not variant or not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle variant not found"
        )
    
    if distance_km <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Distance must be greater than 0"
        )
    
    fixed_cost = variant["fixed_per_km"] * distance_km
    operating_cost = variant["operating_per_km"] * distance_km
    total_cost = variant["total_per_km"] * distance_km
    
    return {
        "category": category["label"],
        "variant": variant["label"],
        "distance_km": distance_km,
        "fixed_per_km": variant["fixed_per_km"],
        "operating_per_km": variant["operating_per_km"],
        "total_per_km": variant["total_per_km"],
        "fixed_cost": round(fixed_cost, 2),
        "operating_cost": round(operating_cost, 2),
        "total_cost": round(total_cost, 2),
        "components": variant["components"],
        "years": {
            "year1": variant["year1"],
            "year2": variant["year2"],
            "year3": variant["year3"],
            "year4": variant["year4"],
            "year5": variant["year5"],
        },
        "initial_cost": variant["initial_cost"],
    }
