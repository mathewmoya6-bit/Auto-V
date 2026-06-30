# app/api/instant_check.py
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import random
import math
import json
from app.core.config import settings
from app.core.supabase import get_supabase_client
from app.core.auth import get_current_user

router = APIRouter(prefix="/instant-check", tags=["Instant Valuation"])

# ─── MODELS ──────────────────────────────────────────────────────────

class VehicleData(BaseModel):
    type: str  # Car, Bike, Tricycle
    make: str
    model: str
    year: int
    engine_capacity: int
    fuel_type: str
    transmission: str
    body_type: str
    body_color: Optional[str] = None
    mileage: int
    condition: str  # Excellent, Good, Fair, Poor
    accident_history: str  # None, Minor, Major, WriteOff
    location: str
    previous_owners: int
    usage_type: str  # Personal, Commercial

class ValuationRequest(BaseModel):
    user_id: str
    vehicle: VehicleData
    phone: str

class ServiceFeeResponse(BaseModel):
    fee: int
    currency: str = "KES"

class ValuationResponse(BaseModel):
    market_value: int
    confidence_score: int
    estimated_range: Dict[str, int]
    transaction_id: Optional[str] = None
    valuation_date: str
    certificate_number: str

# ─── VALUATION ENGINE ──────────────────────────────────────────────

class VehicleValuationEngine:
    """AI-powered vehicle valuation engine for Kenyan market"""
    
    def __init__(self):
        # Base values by vehicle type (starting price in KES)
        self.BASE_VALUES = {
            "Car": 800000,
            "Bike": 150000,
            "Tricycle": 250000
        }
        
        # Depreciation rates per year
        self.DEPRECIATION_RATES = {
            "Car": {
                "year1": 0.20,
                "year2_3": 0.15,
                "year4_5": 0.12,
                "year6_plus": 0.10
            },
            "Bike": {
                "year1": 0.25,
                "year2_3": 0.18,
                "year4_5": 0.14,
                "year6_plus": 0.12
            },
            "Tricycle": {
                "year1": 0.22,
                "year2_3": 0.16,
                "year4_5": 0.13,
                "year6_plus": 0.11
            }
        }
        
        # Make multipliers (premium/discount factors)
        self.MAKE_MULTIPLIERS = {
            # Premium makes
            "BMW": 1.30,
            "Mercedes": 1.30,
            "Audi": 1.25,
            "Land Rover": 1.25,
            "Lexus": 1.25,
            "Porsche": 1.40,
            "Volvo": 1.15,
            "Jeep": 1.10,
            "Subaru": 1.10,
            
            # Mainstream makes
            "Toyota": 1.15,
            "Honda": 1.12,
            "Nissan": 1.08,
            "Mazda": 1.05,
            "Ford": 1.05,
            "Volkswagen": 1.10,
            "Hyundai": 1.05,
            "Kia": 1.05,
            "Mitsubishi": 1.03,
            "Suzuki Car": 1.02,
            "Isuzu": 1.08,
            "Daihatsu": 0.95,
            
            # Budget makes
            "Chevrolet": 0.95,
            "Peugeot": 0.92,
            "Proton": 0.90,
            "Perodua": 0.88,
            "Chery": 0.85,
            
            # Bikes
            "Honda Bike": 1.15,
            "Yamaha": 1.12,
            "Suzuki Bike": 1.10,
            "Kawasaki": 1.08,
            "BMW Motorrad": 1.20,
            "Ducati": 1.25,
            "Triumph": 1.20,
            "Harley Davidson": 1.22,
            "Royal Enfield": 1.05,
            "KTM": 1.08,
            "Bajaj": 0.95,
            "TVS": 0.92,
            "Hero": 0.90,
            
            # Tricycles
            "Piaggio": 1.10,
            "TVS Tricycle": 0.95,
            "Bajaj Tricycle": 0.92
        }
        
        # Model popularity factors (market demand)
        self.MODEL_POPULARITY = {
            "Corolla": 1.20,
            "Axio": 1.15,
            "Fielder": 1.10,
            "Voxy": 1.08,
            "Noah": 1.08,
            "Hiace": 1.15,
            "Land Cruiser": 1.30,
            "Land Cruiser Prado": 1.25,
            "Hilux": 1.20,
            "Rav4": 1.15,
            "X-Trail": 1.10,
            "Patrol": 1.15,
            "C-Class": 1.15,
            "E-Class": 1.20,
            "3 Series": 1.15,
            "5 Series": 1.20,
            "CR-V": 1.12,
            "Civic": 1.10,
            "Forester": 1.10,
            "Outback": 1.05,
            "Ranger": 1.15,
            "Everest": 1.12,
            "Swift": 1.08,
            "Vitara": 1.05,
            "Pajero": 1.10,
            "Outlander": 1.05
        }
        
        # Condition multipliers
        self.CONDITION_MULTIPLIERS = {
            "Excellent": 1.15,
            "Good": 1.00,
            "Fair": 0.85,
            "Poor": 0.70
        }
        
        # Accident history penalties
        self.ACCIDENT_PENALTIES = {
            "None": 0.00,
            "Minor": -0.05,
            "Major": -0.15,
            "WriteOff": -0.30
        }
        
        # Location adjustments
        self.LOCATION_MULTIPLIERS = {
            "Nairobi": 1.05,
            "Mombasa": 1.02,
            "Kisumu": 0.98,
            "Nakuru": 0.99,
            "Eldoret": 0.98,
            "Thika": 1.00,
            "Malindi": 0.97,
            "Other": 0.95
        }
        
        # Usage type adjustments
        self.USAGE_MULTIPLIERS = {
            "Personal": 1.00,
            "Commercial": 0.85
        }
        
        # Engine capacity bonuses
        self.ENGINE_BONUS = {
            "Car": {
                800: 0.80, 1000: 0.85, 1200: 0.90,
                1500: 0.95, 1800: 1.00, 2000: 1.05,
                2500: 1.10, 3000: 1.15, 3500: 1.20,
                4000: 1.25, 5000: 1.30, 6000: 1.35
            },
            "Bike": {
                50: 0.70, 100: 0.80, 125: 0.85,
                150: 0.90, 200: 0.95, 250: 1.00,
                300: 1.05, 400: 1.10, 500: 1.15,
                600: 1.20, 800: 1.25, 1000: 1.30,
                1200: 1.35, 1500: 1.40, 1800: 1.45
            },
            "Tricycle": {
                50: 0.80, 100: 0.85, 125: 0.90,
                150: 0.95, 200: 1.00, 250: 1.05,
                300: 1.10, 400: 1.15, 500: 1.20,
                600: 1.25, 800: 1.30
            }
        }
        
        # Fuel type adjustments
        self.FUEL_MULTIPLIERS = {
            "Petrol": 1.00,
            "Diesel": 1.05,
            "Hybrid": 1.10,
            "Electric": 1.15
        }
        
        # Transmission adjustments
        self.TRANSMISSION_MULTIPLIERS = {
            "Automatic": 1.05,
            "Manual": 0.95,
            "CVT": 1.00
        }
        
        # Mileage depreciation (per km after base)
        self.MILEAGE_DEPRECIATION = {
            "Car": 0.0001,  # 0.01% per km
            "Bike": 0.00015,
            "Tricycle": 0.00012
        }

    def calculate_value(self, vehicle_data: VehicleData) -> Dict[str, Any]:
        """Main valuation calculation"""
        
        # 1. Start with base value
        base_value = self.BASE_VALUES.get(vehicle_data.type, 500000)
        
        # 2. Apply depreciation based on age
        age = 2026 - vehicle_data.year
        depreciation_multiplier = self._calculate_depreciation(vehicle_data.type, age)
        current_value = base_value * depreciation_multiplier
        
        # 3. Apply make multiplier
        make_key = vehicle_data.make
        make_multiplier = self.MAKE_MULTIPLIERS.get(make_key, 1.0)
        current_value *= make_multiplier
        
        # 4. Apply model popularity
        model_key = vehicle_data.model
        model_multiplier = self.MODEL_POPULARITY.get(model_key, 1.0)
        current_value *= model_multiplier
        
        # 5. Apply engine capacity
        engine_multiplier = self._get_engine_multiplier(vehicle_data.type, vehicle_data.engine_capacity)
        current_value *= engine_multiplier
        
        # 6. Apply fuel type
        fuel_multiplier = self.FUEL_MULTIPLIERS.get(vehicle_data.fuel_type, 1.0)
        current_value *= fuel_multiplier
        
        # 7. Apply transmission
        transmission_multiplier = self.TRANSMISSION_MULTIPLIERS.get(vehicle_data.transmission, 1.0)
        current_value *= transmission_multiplier
        
        # 8. Apply condition
        condition_multiplier = self.CONDITION_MULTIPLIERS.get(vehicle_data.condition, 1.0)
        current_value *= condition_multiplier
        
        # 9. Apply accident history
        accident_penalty = self.ACCIDENT_PENALTIES.get(vehicle_data.accident_history, 0.0)
        current_value *= (1 + accident_penalty)
        
        # 10. Apply location
        location_multiplier = self.LOCATION_MULTIPLIERS.get(vehicle_data.location, 1.0)
        current_value *= location_multiplier
        
        # 11. Apply usage type
        usage_multiplier = self.USAGE_MULTIPLIERS.get(vehicle_data.usage_type, 1.0)
        current_value *= usage_multiplier
        
        # 12. Apply mileage depreciation
        mileage_depreciation = self.MILEAGE_DEPRECIATION.get(vehicle_data.type, 0.0001)
        mileage_penalty = min(vehicle_data.mileage * mileage_depreciation, 0.40)  # Max 40% penalty
        current_value *= (1 - mileage_penalty)
        
        # 13. Previous owners penalty
        owner_penalty = min(vehicle_data.previous_owners * 0.03, 0.15)  # 3% per owner, max 15%
        current_value *= (1 - owner_penalty)
        
        # 14. Ensure minimum value (5% of base)
        min_value = base_value * 0.05
        current_value = max(current_value, min_value)
        
        # 15. Round to nearest 1000
        current_value = round(current_value / 1000) * 1000
        
        # 16. Calculate confidence score
        confidence_score = self._calculate_confidence(vehicle_data)
        
        # 17. Calculate range
        range_low = int(current_value * 0.85)
        range_high = int(current_value * 1.15)
        
        return {
            "market_value": int(current_value),
            "confidence_score": confidence_score,
            "estimated_range": {
                "low": range_low,
                "high": range_high
            }
        }

    def _calculate_depreciation(self, vehicle_type: str, age: int) -> float:
        """Calculate depreciation multiplier based on age"""
        rates = self.DEPRECIATION_RATES.get(vehicle_type, self.DEPRECIATION_RATES["Car"])
        
        if age <= 0:
            return 1.0
        elif age == 1:
            return 1.0 - rates["year1"]
        elif age <= 3:
            return (1.0 - rates["year1"]) * ((1.0 - rates["year2_3"]) ** (age - 1))
        elif age <= 5:
            return (1.0 - rates["year1"]) * ((1.0 - rates["year2_3"]) ** 2) * ((1.0 - rates["year4_5"]) ** (age - 3))
        else:
            return (1.0 - rates["year1"]) * ((1.0 - rates["year2_3"]) ** 2) * ((1.0 - rates["year4_5"]) ** 2) * ((1.0 - rates["year6_plus"]) ** (age - 5))

    def _get_engine_multiplier(self, vehicle_type: str, engine_capacity: int) -> float:
        """Get engine capacity multiplier"""
        engine_bonus_map = self.ENGINE_BONUS.get(vehicle_type, {})
        
        # Find closest matching engine size
        closest = min(engine_bonus_map.keys(), key=lambda x: abs(x - engine_capacity))
        return engine_bonus_map.get(closest, 1.0)

    def _calculate_confidence(self, vehicle_data: VehicleData) -> int:
        """Calculate confidence score based on data completeness and quality"""
        score = 70  # Base confidence
        
        # Add for known make
        if vehicle_data.make in self.MAKE_MULTIPLIERS:
            score += 5
        
        # Add for known model
        if vehicle_data.model in self.MODEL_POPULARITY:
            score += 5
        
        # Add for complete data
        if vehicle_data.body_color:
            score += 2
        
        # Condition clarity
        if vehicle_data.condition in ["Excellent", "Good"]:
            score += 5
        elif vehicle_data.condition in ["Fair", "Poor"]:
            score += 3
        
        # Accident history clarity
        if vehicle_data.accident_history != "None":
            score += 3
        
        # Previous owners
        if vehicle_data.previous_owners <= 2:
            score += 3
        elif vehicle_data.previous_owners <= 4:
            score += 1
        
        # Mileage reasonableness
        avg_mileage_per_year = vehicle_data.mileage / max(1, (2026 - vehicle_data.year))
        if avg_mileage_per_year < 15000:
            score += 5
        elif avg_mileage_per_year < 25000:
            score += 3
        else:
            score += 1
        
        # Location specificity
        if vehicle_data.location in self.LOCATION_MULTIPLIERS:
            score += 2
        
        # Cap at 98%
        return min(score, 98)

# ─── API ENDPOINTS ──────────────────────────────────────────────────

@router.get("/service-fee", response_model=ServiceFeeResponse)
async def get_service_fee():
    """Get the current service fee for instant valuation"""
    # Could be dynamic based on vehicle type or market conditions
    fee = 500
    if settings.ENV == "production":
        fee = 500
    else:
        fee = 100  # Lower fee for testing
    
    return ServiceFeeResponse(fee=fee)

@router.post("/valuate", response_model=ValuationResponse)
async def valuate_vehicle(
    request: ValuationRequest,
    authorization: Optional[str] = Header(None)
):
    """Process vehicle valuation with AI engine"""
    
    try:
        # Validate authentication
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization required")
        
        # Get user from token
        # user = await get_current_user(authorization)
        
        # Initialize valuation engine
        engine = VehicleValuationEngine()
        
        # Calculate valuation
        result = engine.calculate_value(request.vehicle)
        
        # Generate certificate number
        cert_number = f"AUTO-VAL-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
        
        # Store in database (optional)
        # await store_valuation(request, result, cert_number)
        
        # Process M-Pesa payment (optional)
        transaction_id = None
        # if request.phone:
        #     transaction_id = await process_payment(request.phone, 500)
        
        return ValuationResponse(
            market_value=result["market_value"],
            confidence_score=result["confidence_score"],
            estimated_range=result["estimated_range"],
            transaction_id=transaction_id,
            valuation_date=datetime.now().isoformat(),
            certificate_number=cert_number
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────

async def store_valuation(request: ValuationRequest, result: Dict, cert_number: str):
    """Store valuation in database"""
    supabase = get_supabase_client()
    
    data = {
        "user_id": request.user_id,
        "vehicle_make": request.vehicle.make,
        "vehicle_model": request.vehicle.model,
        "vehicle_year": request.vehicle.year,
        "engine_capacity": request.vehicle.engine_capacity,
        "mileage": request.vehicle.mileage,
        "condition": request.vehicle.condition,
        "accident_history": request.vehicle.accident_history,
        "location": request.vehicle.location,
        "market_value": result["market_value"],
        "confidence_score": result["confidence_score"],
        "certificate_number": cert_number,
        "created_at": datetime.now().isoformat()
    }
    
    try:
        response = supabase.table("valuations").insert(data).execute()
        return response
    except Exception as e:
        print(f"Error storing valuation: {e}")
        return None

async def process_payment(phone: str, amount: int) -> str:
    """Process M-Pesa payment"""
    # Integrate with M-Pesa API here
    # Return transaction ID
    return f"TXN-{random.randint(100000, 999999)}"
