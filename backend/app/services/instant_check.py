# ============================================================
# AUTO-V COMMERCIAL GRADE VALUATION ENGINE
# app/api/instant_check.py
# ============================================================

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import random
import math
import json
import hashlib
import hmac
from enum import Enum
from app.core.config import settings
from app.core.supabase import get_supabase_client
from app.core.auth import get_current_user

router = APIRouter(prefix="/instant-check", tags=["Instant Valuation"])

# ─── ENUMS & CONSTANTS ──────────────────────────────────────────────

class VehicleType(str, Enum):
    CAR = "Car"
    BIKE = "Bike"
    TRICYCLE = "Tricycle"
    SUV = "SUV"
    PICKUP = "Pickup"
    VAN = "Van"
    TRUCK = "Truck"

class VehicleGrade(str, Enum):
    GRADE_5 = "5"
    GRADE_45 = "4.5"
    GRADE_4 = "4"
    GRADE_35 = "3.5"
    GRADE_3 = "3"
    GRADE_R = "R"
    GRADE_RA = "RA"

class ConditionGrade(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    SALVAGE = "Salvage"

class FuelType(str, Enum):
    PETROL = "Petrol"
    DIESEL = "Diesel"
    HYBRID = "Hybrid"
    ELECTRIC = "Electric"
    LPG = "LPG"

class TransmissionType(str, Enum):
    AUTOMATIC = "Automatic"
    MANUAL = "Manual"
    CVT = "CVT"
    DSG = "DSG"

class UsageType(str, Enum):
    PERSONAL = "Personal"
    COMMERCIAL = "Commercial"
    FLEET = "Fleet"
    RENTAL = "Rental"
    GOVERNMENT = "Government"

class AccidentHistory(str, Enum):
    NONE = "None"
    MINOR = "Minor"
    MODERATE = "Moderate"
    MAJOR = "Major"
    WRITE_OFF = "WriteOff"

# ─── MODELS ──────────────────────────────────────────────────────────

class VehicleData(BaseModel):
    type: VehicleType
    make: str
    model: str
    year: int = Field(..., ge=1950, le=2026)
    trim: Optional[str] = None
    grade: Optional[VehicleGrade] = None
    engine_capacity: int
    fuel_type: FuelType
    transmission: TransmissionType
    body_type: str
    body_color: Optional[str] = None
    mileage: int = Field(..., ge=0)
    condition: ConditionGrade
    accident_history: AccidentHistory
    location: str
    previous_owners: int = Field(..., ge=0)
    usage_type: UsageType
    imported: bool = False
    import_country: Optional[str] = None
    modifications: Optional[str] = None
    service_history: bool = False
    vin: Optional[str] = None

class ValuationRequest(BaseModel):
    user_id: str
    vehicle: VehicleData
    phone: str
    include_comparables: bool = True
    include_ai_explanation: bool = True

class ServiceFeeResponse(BaseModel):
    fee: int
    currency: str = "KES"
    breakdown: Optional[Dict[str, Any]] = None

class ComparableVehicle(BaseModel):
    make: str
    model: str
    year: int
    price: int
    source: str  # Dealer, Private, Auction
    mileage: int
    condition: str

class MarketTrend(BaseModel):
    trend: str  # Rising, Stable, Falling
    percentage: float
    timeframe: str
    factors: List[str]

class AIExplanation(BaseModel):
    positives: List[str]
    negatives: List[str]
    summary: str

class VehicleIntelligenceScore(BaseModel):
    overall: int
    health: int
    liquidity: int
    market_demand: int
    repair_risk: int
    insurance_risk: str

class ValuationResponse(BaseModel):
    # Core valuation
    market_value: int
    price_range: Dict[str, int]
    confidence_score: int
    
    # Market intelligence
    market_trend: Optional[MarketTrend] = None
    comparables: Optional[List[ComparableVehicle]] = None
    demand_score: int
    liquidity_score: int
    
    # Vehicle intelligence
    intelligence_score: VehicleIntelligenceScore
    
    # AI explanation
    ai_explanation: Optional[AIExplanation] = None
    
    # Recommendation
    recommendation: str
    holding_period: Optional[str] = None
    
    # Verification
    certificate_number: str
    valuation_date: str
    transaction_id: Optional[str] = None
    qr_code: Optional[str] = None

# ─── MARKET DATABASE ──────────────────────────────────────────────────

class MarketDatabase:
    """Live market data for vehicle valuations"""
    
    def __init__(self):
        # In production, this would be a PostgreSQL table with regular updates
        self.market_data = self._load_market_data()
    
    def _load_market_data(self) -> Dict[str, Any]:
        """Load market data from database or cache"""
        # This is sample data - in production, load from Supabase
        return {
            "Toyota": {
                "Corolla": {
                    "base_prices": {
                        2018: {"dealer": 1540000, "private": 1420000, "auction": 1360000},
                        2019: {"dealer": 1620000, "private": 1500000, "auction": 1440000},
                        2020: {"dealer": 1710000, "private": 1580000, "auction": 1520000},
                        2021: {"dealer": 1800000, "private": 1670000, "auction": 1600000},
                        2022: {"dealer": 1900000, "private": 1760000, "auction": 1680000},
                    },
                    "demand": {
                        "score": 92,
                        "days_on_market": 8,
                        "inventory": "Low",
                        "trend": "+4%"
                    },
                    "depreciation_curve": {
                        "year1": 0.15,
                        "year2_3": 0.12,
                        "year4_5": 0.10,
                        "year6_plus": 0.08
                    }
                },
                "Axio": {
                    "base_prices": {
                        2018: {"dealer": 1480000, "private": 1360000, "auction": 1300000},
                        2019: {"dealer": 1560000, "private": 1440000, "auction": 1380000},
                        2020: {"dealer": 1650000, "private": 1520000, "auction": 1460000},
                        2021: {"dealer": 1740000, "private": 1610000, "auction": 1540000},
                        2022: {"dealer": 1840000, "private": 1700000, "auction": 1620000},
                    },
                    "demand": {
                        "score": 88,
                        "days_on_market": 10,
                        "inventory": "Medium",
                        "trend": "+3%"
                    },
                    "depreciation_curve": {
                        "year1": 0.16,
                        "year2_3": 0.13,
                        "year4_5": 0.10,
                        "year6_plus": 0.08
                    }
                },
                "Land Cruiser Prado": {
                    "base_prices": {
                        2018: {"dealer": 4200000, "private": 3900000, "auction": 3700000},
                        2019: {"dealer": 4500000, "private": 4200000, "auction": 4000000},
                        2020: {"dealer": 4800000, "private": 4500000, "auction": 4300000},
                        2021: {"dealer": 5100000, "private": 4800000, "auction": 4600000},
                        2022: {"dealer": 5500000, "private": 5100000, "auction": 4900000},
                    },
                    "demand": {
                        "score": 95,
                        "days_on_market": 5,
                        "inventory": "Very Low",
                        "trend": "+8%"
                    },
                    "depreciation_curve": {
                        "year1": 0.10,
                        "year2_3": 0.08,
                        "year4_5": 0.07,
                        "year6_plus": 0.06
                    }
                },
                "Hilux": {
                    "base_prices": {
                        2018: {"dealer": 2800000, "private": 2600000, "auction": 2400000},
                        2019: {"dealer": 3000000, "private": 2800000, "auction": 2600000},
                        2020: {"dealer": 3200000, "private": 3000000, "auction": 2800000},
                        2021: {"dealer": 3500000, "private": 3200000, "auction": 3000000},
                        2022: {"dealer": 3800000, "private": 3500000, "auction": 3300000},
                    },
                    "demand": {
                        "score": 90,
                        "days_on_market": 7,
                        "inventory": "Low",
                        "trend": "+6%"
                    },
                    "depreciation_curve": {
                        "year1": 0.12,
                        "year2_3": 0.10,
                        "year4_5": 0.08,
                        "year6_plus": 0.07
                    }
                }
            }
        }
    
    def get_vehicle_data(self, make: str, model: str, year: int) -> Dict[str, Any]:
        """Get market data for a specific vehicle"""
        make_data = self.market_data.get(make, {})
        model_data = make_data.get(model, {})
        
        # Get base prices for the year
        prices = model_data.get("base_prices", {}).get(year, {})
        if not prices:
            # Fallback to nearest year
            years = sorted(model_data.get("base_prices", {}).keys())
            if years:
                nearest = min(years, key=lambda x: abs(x - year))
                prices = model_data["base_prices"][nearest]
        
        demand = model_data.get("demand", {
            "score": 80,
            "days_on_market": 15,
            "inventory": "Medium",
            "trend": "0%"
        })
        
        depreciation = model_data.get("depreciation_curve", {
            "year1": 0.15,
            "year2_3": 0.12,
            "year4_5": 0.10,
            "year6_plus": 0.08
        })
        
        return {
            "prices": prices,
            "demand": demand,
            "depreciation": depreciation,
            "has_data": bool(prices)
        }

# ─── COMMERCIAL VALUATION ENGINE ────────────────────────────────────

class CommercialValuationEngine:
    """Commercial-grade vehicle valuation engine with market intelligence"""
    
    def __init__(self):
        self.market_db = MarketDatabase()
        self._initialize_make_multipliers()
        self._initialize_trim_multipliers()
        self._initialize_grade_multipliers()
    
    def _initialize_make_multipliers(self):
        """Premium/discount factors by make"""
        self.MAKE_MULTIPLIERS = {
            # Premium
            "BMW": 1.30, "Mercedes": 1.30, "Audi": 1.25,
            "Land Rover": 1.25, "Lexus": 1.25, "Porsche": 1.40,
            "Volvo": 1.15, "Jeep": 1.10, "Subaru": 1.10,
            # Mainstream
            "Toyota": 1.15, "Honda": 1.12, "Nissan": 1.08,
            "Mazda": 1.05, "Ford": 1.05, "Volkswagen": 1.10,
            "Hyundai": 1.05, "Kia": 1.05, "Mitsubishi": 1.03,
            "Suzuki": 1.02, "Isuzu": 1.08, "Daihatsu": 0.95,
            # Budget
            "Chevrolet": 0.95, "Peugeot": 0.92, "Proton": 0.90,
            "Perodua": 0.88, "Chery": 0.85,
            # Bikes
            "Honda Bike": 1.15, "Yamaha": 1.12, "Suzuki Bike": 1.10,
            "Kawasaki": 1.08, "BMW Motorrad": 1.20, "Ducati": 1.25,
            "Triumph": 1.20, "Harley Davidson": 1.22, "Royal Enfield": 1.05,
            "KTM": 1.08, "Bajaj": 0.95, "TVS": 0.92, "Hero": 0.90,
            # Tricycles
            "Piaggio": 1.10, "TVS Tricycle": 0.95, "Bajaj Tricycle": 0.92
        }
    
    def _initialize_trim_multipliers(self):
        """Trim level multipliers"""
        self.TRIM_MULTIPLIERS = {
            # Toyota Prado
            "TX": 1.00, "TXL": 1.08, "VX": 1.12,
            "VX-L": 1.18, "TZ-G": 1.15,
            # Toyota Corolla
            "Base": 1.00, "GL": 1.05, "GLS": 1.10,
            "SR": 1.08, "S": 1.12,
            # Toyota Camry
            "LE": 1.00, "SE": 1.05, "XLE": 1.10,
            "XSE": 1.12, "TRD": 1.08,
            # Honda CR-V
            "LX": 1.00, "EX": 1.06, "EX-L": 1.10,
            "Touring": 1.14, "Elite": 1.12,
            # BMW 3 Series
            "Base": 1.00, "Sport": 1.06, "M Sport": 1.12,
            "Luxury": 1.08, "M3": 1.25,
            # Default
            "Default": 1.00
        }
    
    def _initialize_grade_multipliers(self):
        """Japanese vehicle grade multipliers"""
        self.GRADE_MULTIPLIERS = {
            "5": 1.15,
            "4.5": 1.08,
            "4": 1.00,
            "3.5": 0.92,
            "3": 0.85,
            "R": 0.70,
            "RA": 0.60
        }
    
    def calculate_value(self, vehicle: VehicleData) -> Dict[str, Any]:
        """Calculate comprehensive vehicle valuation"""
        
        # 1. Get market data
        market_data = self.market_db.get_vehicle_data(vehicle.make, vehicle.model, vehicle.year)
        
        # 2. Calculate base price from market data
        base_price = self._get_base_price(market_data)
        
        # 3. Apply depreciation
        age = 2026 - vehicle.year
        depreciation = self._calculate_depreciation(
            vehicle.type.value,
            age,
            market_data.get("depreciation", {})
        )
        current_value = base_price * depreciation
        
        # 4. Apply make multiplier
        make_mult = self.MAKE_MULTIPLIERS.get(vehicle.make, 1.0)
        current_value *= make_mult
        
        # 5. Apply trim multiplier
        trim_mult = self.TRIM_MULTIPLIERS.get(vehicle.trim or "Default", 1.0)
        current_value *= trim_mult
        
        # 6. Apply grade multiplier (Japanese imports)
        if vehicle.grade:
            grade_mult = self.GRADE_MULTIPLIERS.get(vehicle.grade.value, 1.0)
            current_value *= grade_mult
        
        # 7. Apply engine capacity
        engine_mult = self._get_engine_multiplier(vehicle.type.value, vehicle.engine_capacity)
        current_value *= engine_mult
        
        # 8. Apply fuel type
        fuel_mult = self._get_fuel_multiplier(vehicle.fuel_type)
        current_value *= fuel_mult
        
        # 9. Apply transmission
        trans_mult = self._get_transmission_multiplier(vehicle.transmission)
        current_value *= trans_mult
        
        # 10. Apply condition
        condition_mult = self._get_condition_multiplier(vehicle.condition)
        current_value *= condition_mult
        
        # 11. Apply accident history
        accident_adj = self._get_accident_adjustment(vehicle.accident_history)
        current_value *= (1 + accident_adj)
        
        # 12. Apply location
        location_mult = self._get_location_multiplier(vehicle.location)
        current_value *= location_mult
        
        # 13. Apply usage type
        usage_mult = self._get_usage_multiplier(vehicle.usage_type)
        current_value *= usage_mult
        
        # 14. Apply mileage with curve
        mileage_adj = self._calculate_mileage_adjustment(
            vehicle.type.value,
            vehicle.mileage,
            vehicle.year
        )
        current_value *= (1 - mileage_adj)
        
        # 15. Previous owners penalty
        owner_penalty = min(vehicle.previous_owners * 0.025, 0.15)
        current_value *= (1 - owner_penalty)
        
        # 16. Imported vehicle adjustment
        if vehicle.imported:
            import_adj = self._get_import_adjustment(vehicle.import_country)
            current_value *= import_adj
        
        # 17. Service history bonus
        if vehicle.service_history:
            current_value *= 1.03
        
        # 18. Ensure minimum value
        min_value = base_price * 0.05
        current_value = max(current_value, min_value)
        
        # 19. Round to nearest 1000
        current_value = round(current_value / 1000) * 1000
        
        # 20. Calculate intelligence scores
        intelligence_score = self._calculate_intelligence_score(vehicle, current_value, market_data)
        
        # 21. Calculate market demand
        demand_score = self._calculate_demand_score(vehicle, market_data)
        
        # 22. Calculate liquidity
        liquidity_score = self._calculate_liquidity_score(vehicle, market_data)
        
        # 23. Generate range
        range_low = int(current_value * 0.88)
        range_high = int(current_value * 1.08)
        
        # 24. Calculate confidence
        confidence = self._calculate_confidence(vehicle, market_data)
        
        # 25. Generate AI explanation
        ai_explanation = self._generate_ai_explanation(vehicle, current_value, market_data)
        
        # 26. Generate recommendation
        recommendation = self._generate_recommendation(vehicle, current_value, market_data)
        
        return {
            "market_value": int(current_value),
            "price_range": {"low": range_low, "high": range_high},
            "confidence_score": confidence,
            "demand_score": demand_score,
            "liquidity_score": liquidity_score,
            "intelligence_score": intelligence_score,
            "ai_explanation": ai_explanation,
            "recommendation": recommendation,
            "holding_period": self._calculate_holding_period(vehicle, market_data),
            "market_trend": self._get_market_trend(vehicle, market_data)
        }
    
    def _get_base_price(self, market_data: Dict[str, Any]) -> float:
        """Get base price from market data"""
        prices = market_data.get("prices", {})
        dealer_price = prices.get("dealer", 0)
        private_price = prices.get("private", 0)
        auction_price = prices.get("auction", 0)
        
        # Weighted average: Dealer (0.5), Private (0.3), Auction (0.2)
        base_price = (dealer_price * 0.5) + (private_price * 0.3) + (auction_price * 0.2)
        
        if base_price == 0:
            # Fallback: use generic base by type
            base_prices = {"Car": 1200000, "SUV": 2000000, "Pickup": 1800000,
                          "Bike": 200000, "Tricycle": 300000, "Truck": 3000000}
            return base_prices.get("Car", 1000000)
        
        return base_price
    
    def _calculate_depreciation(self, vehicle_type: str, age: int, curve: Dict) -> float:
        """Calculate depreciation using vehicle-specific curve"""
        if age <= 0:
            return 1.0
        
        # Use vehicle-specific curve if available
        if curve:
            if age == 1:
                return 1.0 - curve.get("year1", 0.15)
            elif age <= 3:
                return (1.0 - curve.get("year1", 0.15)) * ((1.0 - curve.get("year2_3", 0.12)) ** (age - 1))
            elif age <= 5:
                return (1.0 - curve.get("year1", 0.15)) * ((1.0 - curve.get("year2_3", 0.12)) ** 2) * ((1.0 - curve.get("year4_5", 0.10)) ** (age - 3))
            else:
                return (1.0 - curve.get("year1", 0.15)) * ((1.0 - curve.get("year2_3", 0.12)) ** 2) * ((1.0 - curve.get("year4_5", 0.10)) ** 2) * ((1.0 - curve.get("year6_plus", 0.08)) ** (age - 5))
        
        # Generic depreciation
        if age == 1:
            return 0.85
        elif age <= 3:
            return 0.85 * (0.88 ** (age - 1))
        elif age <= 5:
            return 0.85 * (0.88 ** 2) * (0.90 ** (age - 3))
        else:
            return 0.85 * (0.88 ** 2) * (0.90 ** 2) * (0.92 ** (age - 5))
    
    def _get_engine_multiplier(self, vehicle_type: str, engine_cc: int) -> float:
        """Get engine capacity multiplier"""
        engine_bonus = {
            "Car": {
                800: 0.80, 1000: 0.85, 1200: 0.90, 1500: 0.95,
                1800: 1.00, 2000: 1.05, 2500: 1.10, 3000: 1.15,
                3500: 1.20, 4000: 1.25, 5000: 1.30, 6000: 1.35
            },
            "Bike": {
                50: 0.70, 100: 0.80, 125: 0.85, 150: 0.90,
                200: 0.95, 250: 1.00, 300: 1.05, 400: 1.10,
                500: 1.15, 600: 1.20, 800: 1.25, 1000: 1.30,
                1200: 1.35, 1500: 1.40, 1800: 1.45
            },
            "Tricycle": {
                50: 0.80, 100: 0.85, 125: 0.90, 150: 0.95,
                200: 1.00, 250: 1.05, 300: 1.10, 400: 1.15,
                500: 1.20, 600: 1.25, 800: 1.30
            }
        }
        
        engine_map = engine_bonus.get(vehicle_type, engine_bonus["Car"])
        closest = min(engine_map.keys(), key=lambda x: abs(x - engine_cc))
        return engine_map.get(closest, 1.0)
    
    def _get_fuel_multiplier(self, fuel_type: FuelType) -> float:
        """Get fuel type multiplier"""
        multipliers = {
            FuelType.PETROL: 1.00,
            FuelType.DIESEL: 1.05,
            FuelType.HYBRID: 1.10,
            FuelType.ELECTRIC: 1.15,
            FuelType.LPG: 0.95
        }
        return multipliers.get(fuel_type, 1.00)
    
    def _get_transmission_multiplier(self, transmission: TransmissionType) -> float:
        """Get transmission multiplier"""
        multipliers = {
            TransmissionType.AUTOMATIC: 1.05,
            TransmissionType.MANUAL: 0.95,
            TransmissionType.CVT: 1.00,
            TransmissionType.DSG: 1.03
        }
        return multipliers.get(transmission, 1.00)
    
    def _get_condition_multiplier(self, condition: ConditionGrade) -> float:
        """Get condition multiplier"""
        multipliers = {
            ConditionGrade.EXCELLENT: 1.15,
            ConditionGrade.GOOD: 1.00,
            ConditionGrade.FAIR: 0.85,
            ConditionGrade.POOR: 0.70,
            ConditionGrade.SALVAGE: 0.40
        }
        return multipliers.get(condition, 1.00)
    
    def _get_accident_adjustment(self, accident: AccidentHistory) -> float:
        """Get accident history adjustment"""
        adjustments = {
            AccidentHistory.NONE: 0.00,
            AccidentHistory.MINOR: -0.05,
            AccidentHistory.MODERATE: -0.10,
            AccidentHistory.MAJOR: -0.20,
            AccidentHistory.WRITE_OFF: -0.35
        }
        return adjustments.get(accident, 0.00)
    
    def _get_location_multiplier(self, location: str) -> float:
        """Get location multiplier"""
        multipliers = {
            "Nairobi": 1.05,
            "Mombasa": 1.02,
            "Kisumu": 0.98,
            "Nakuru": 0.99,
            "Eldoret": 0.98,
            "Thika": 1.00,
            "Malindi": 0.97,
            "Kiambu": 1.02,
            "Kajiado": 0.98,
            "Machakos": 0.98,
        }
        return multipliers.get(location, 0.95)
    
    def _get_usage_multiplier(self, usage: UsageType) -> float:
        """Get usage type multiplier"""
        multipliers = {
            UsageType.PERSONAL: 1.00,
            UsageType.COMMERCIAL: 0.85,
            UsageType.FLEET: 0.80,
            UsageType.RENTAL: 0.82,
            UsageType.GOVERNMENT: 0.90
        }
        return multipliers.get(usage, 1.00)
    
    def _calculate_mileage_adjustment(self, vehicle_type: str, mileage: int, year: int) -> float:
        """Calculate mileage adjustment using a curve"""
        # Expected mileage: 15,000 km/year
        age = 2026 - year
        expected_mileage = age * 15000
        
        if mileage <= expected_mileage:
            # Bonus for lower than expected mileage
            ratio = mileage / max(expected_mileage, 1)
            if ratio < 0.5:
                return -0.05  # 5% bonus
            elif ratio < 0.8:
                return -0.02  # 2% bonus
            else:
                return 0.00
        else:
            # Penalty for higher than expected mileage
            excess = (mileage - expected_mileage) / max(expected_mileage, 1)
            return min(0.35, excess * 0.4)
    
    def _get_import_adjustment(self, import_country: Optional[str]) -> float:
        """Get import country adjustment"""
        if not import_country:
            return 1.00
        
        adjustments = {
            "Japan": 1.05,
            "UK": 1.02,
            "Germany": 1.03,
            "USA": 0.98,
            "UAE": 0.95,
            "South Africa": 0.92,
            "Thailand": 0.90,
            "India": 0.85,
            "China": 0.80,
        }
        return adjustments.get(import_country, 0.95)
    
    def _calculate_intelligence_score(self, vehicle: VehicleData, value: float, market_data: Dict) -> Dict[str, Any]:
        """Calculate comprehensive vehicle intelligence scores"""
        
        # Health score (condition + service history + mileage)
        health = 70
        if vehicle.condition == ConditionGrade.EXCELLENT:
            health += 20
        elif vehicle.condition == ConditionGrade.GOOD:
            health += 10
        elif vehicle.condition == ConditionGrade.FAIR:
            health += 0
        else:
            health -= 10
        
        if vehicle.service_history:
            health += 5
        
        # Mileage health
        age = 2026 - vehicle.year
        expected_mileage = age * 15000
        if vehicle.mileage < expected_mileage * 0.5:
            health += 10
        elif vehicle.mileage < expected_mileage * 0.8:
            health += 5
        elif vehicle.mileage > expected_mileage * 1.5:
            health -= 5
        elif vehicle.mileage > expected_mileage * 2:
            health -= 10
        
        health = max(0, min(100, health))
        
        # Liquidity score (how fast it sells)
        liquidity = 70
        days_on_market = market_data.get("demand", {}).get("days_on_market", 15)
        if days_on_market < 5:
            liquidity += 20
        elif days_on_market < 10:
            liquidity += 10
        elif days_on_market < 20:
            liquidity += 0
        elif days_on_market < 30:
            liquidity -= 10
        else:
            liquidity -= 20
        
        # Market demand
        demand = market_data.get("demand", {}).get("score", 80)
        
        # Repair risk (based on make, model, age)
        repair_risk = 20
        if vehicle.make in ["Toyota", "Honda", "Suzuki"]:
            repair_risk -= 10
        if vehicle.make in ["BMW", "Mercedes", "Audi", "Land Rover"]:
            repair_risk += 15
        if vehicle.age > 10:
            repair_risk += 10
        elif vehicle.age > 5:
            repair_risk += 5
        
        # Insurance risk
        if vehicle.accident_history == AccidentHistory.NONE:
            insurance_risk = "Low"
        elif vehicle.accident_history == AccidentHistory.MINOR:
            insurance_risk = "Low-Medium"
        elif vehicle.accident_history == AccidentHistory.MODERATE:
            insurance_risk = "Medium"
        elif vehicle.accident_history == AccidentHistory.MAJOR:
            insurance_risk = "High"
        else:
            insurance_risk = "Very High"
        
        # Overall score
        overall = int((health * 0.25) + (liquidity * 0.20) + (demand * 0.25) + (100 - repair_risk) * 0.30)
        overall = max(0, min(100, overall))
        
        return {
            "overall": overall,
            "health": health,
            "liquidity": liquidity,
            "market_demand": demand,
            "repair_risk": repair_risk,
            "insurance_risk": insurance_risk
        }
    
    def _calculate_demand_score(self, vehicle: VehicleData, market_data: Dict) -> int:
        """Calculate market demand score"""
        # Start with market data demand
        base_demand = market_data.get("demand", {}).get("score", 80)
        
        # Adjust based on vehicle type
        type_demand = {
            "Car": 0,
            "SUV": 10,
            "Pickup": 8,
            "Van": 5,
            "Truck": 3,
            "Bike": 5,
            "Tricycle": 2
        }
        base_demand += type_demand.get(vehicle.type.value, 0)
        
        # Adjust based on fuel type
        fuel_demand = {
            FuelType.PETROL: 0,
            FuelType.DIESEL: 5,
            FuelType.HYBRID: 10,
            FuelType.ELECTRIC: 8,
            FuelType.LPG: 3
        }
        base_demand += fuel_demand.get(vehicle.fuel_type, 0)
        
        # Adjust based on condition
        condition_demand = {
            ConditionGrade.EXCELLENT: 10,
            ConditionGrade.GOOD: 5,
            ConditionGrade.FAIR: 0,
            ConditionGrade.POOR: -10,
            ConditionGrade.SALVAGE: -20
        }
        base_demand += condition_demand.get(vehicle.condition, 0)
        
        # Adjust based on accident history
        accident_demand = {
            AccidentHistory.NONE: 10,
            AccidentHistory.MINOR: 0,
            AccidentHistory.MODERATE: -5,
            AccidentHistory.MAJOR: -15,
            AccidentHistory.WRITE_OFF: -25
        }
        base_demand += accident_demand.get(vehicle.accident_history, 0)
        
        return max(0, min(100, base_demand))
    
    def _calculate_liquidity_score(self, vehicle: VehicleData, market_data: Dict) -> int:
        """Calculate liquidity score"""
        days_on_market = market_data.get("demand", {}).get("days_on_market", 15)
        
        if days_on_market < 5:
            return 95
        elif days_on_market < 10:
            return 85
        elif days_on_market < 15:
            return 75
        elif days_on_market < 20:
            return 65
        elif days_on_market < 30:
            return 50
        else:
            return 35
    
    def _calculate_confidence(self, vehicle: VehicleData, market_data: Dict) -> int:
        """Calculate confidence score"""
        confidence = 60
        
        # Market data availability
        if market_data.get("has_data", False):
            confidence += 15
        else:
            confidence -= 10
        
        # Data completeness
        if vehicle.trim:
            confidence += 5
        if vehicle.grade:
            confidence += 5
        if vehicle.vin:
            confidence += 5
        if vehicle.service_history:
            confidence += 3
        
        # Condition clarity
        if vehicle.condition in [ConditionGrade.EXCELLENT, ConditionGrade.GOOD]:
            confidence += 5
        
        # Accident history clarity
        if vehicle.accident_history != AccidentHistory.NONE:
            confidence += 3
        
        # Previous owners
        if vehicle.previous_owners <= 1:
            confidence += 5
        elif vehicle.previous_owners <= 2:
            confidence += 3
        
        # Mileage reasonableness
        age = 2026 - vehicle.year
        expected_mileage = age * 15000
        if vehicle.mileage < expected_mileage * 0.5:
            confidence += 5
        elif vehicle.mileage > expected_mileage * 2:
            confidence -= 5
        
        # Location specificity
        if vehicle.location in self._get_location_multiplier(""):
            confidence += 3
        
        # Import details
        if vehicle.imported and vehicle.import_country:
            confidence += 3
        
        return max(0, min(98, confidence))
    
    def _generate_ai_explanation(self, vehicle: VehicleData, value: float, market_data: Dict) -> AIExplanation:
        """Generate AI explanation for the valuation"""
        positives = []
        negatives = []
        
        # Condition
        if vehicle.condition == ConditionGrade.EXCELLENT:
            positives.append("Excellent condition adds significant value")
        elif vehicle.condition == ConditionGrade.GOOD:
            positives.append("Good condition maintains market value")
        elif vehicle.condition == ConditionGrade.FAIR:
            negatives.append("Fair condition reduces value")
        else:
            negatives.append("Poor condition significantly reduces value")
        
        # Mileage
        age = 2026 - vehicle.year
        expected_mileage = age * 15000
        if vehicle.mileage < expected_mileage * 0.5:
            positives.append("Low mileage adds premium value")
        elif vehicle.mileage < expected_mileage * 0.8:
            positives.append("Below average mileage is a positive factor")
        elif vehicle.mileage > expected_mileage * 1.5:
            negatives.append("High mileage reduces value")
        elif vehicle.mileage > expected_mileage * 2:
            negatives.append("Very high mileage significantly reduces value")
        
        # Accident history
        if vehicle.accident_history == AccidentHistory.NONE:
            positives.append("No accident history increases buyer confidence")
        elif vehicle.accident_history == AccidentHistory.MINOR:
            negatives.append("Minor accident history has small impact on value")
        else:
            negatives.append("Significant accident history reduces value")
        
        # Location
        if vehicle.location in ["Nairobi", "Mombasa"]:
            positives.append("Premium location market adds value")
        
        # Previous owners
        if vehicle.previous_owners <= 1:
            positives.append("Few previous owners increases trust and value")
        elif vehicle.previous_owners > 3:
            negatives.append("Multiple previous owners may concern buyers")
        
        # Make and model popularity
        make_mult = self.MAKE_MULTIPLIERS.get(vehicle.make, 1.0)
        if make_mult > 1.10:
            positives.append(f"{vehicle.make} vehicles are in high demand")
        elif make_mult < 0.90:
            negatives.append(f"{vehicle.make} has lower market demand")
        
        # Service history
        if vehicle.service_history:
            positives.append("Full service history adds value and trust")
        else:
            negatives.append("No service history may reduce buyer confidence")
        
        # Fuel type
        if vehicle.fuel_type in [FuelType.HYBRID, FuelType.ELECTRIC]:
            positives.append("Fuel-efficient technology adds value")
        
        # Imports
        if vehicle.imported and vehicle.import_country in ["Japan", "Germany"]:
            positives.append("Import from premium market adds value")
        
        # Cap positives and negatives
        positives = positives[:5]  # Max 5 positive points
        negatives = negatives[:5]  # Max 5 negative points
        
        # Generate summary
        if len(positives) > len(negatives):
            summary = "This vehicle is in above-average condition with positive market factors. "
            if vehicle.condition in [ConditionGrade.EXCELLENT, ConditionGrade.GOOD]:
                summary += "The good condition and market demand support the valuation."
            else:
                summary += "Despite some condition issues, market demand supports the valuation."
        else:
            summary = "This vehicle has some factors that may affect its market value. "
            if vehicle.accident_history != AccidentHistory.NONE:
                summary += "The accident history is a key factor in the valuation."
            else:
                summary += "Consider addressing the listed issues to increase value."
        
        return AIExplanation(
            positives=positives,
            negatives=negatives,
            summary=summary
        )
    
    def _generate_recommendation(self, vehicle: VehicleData, value: float, market_data: Dict) -> str:
        """Generate actionable recommendation"""
        demand_score = self._calculate_demand_score(vehicle, market_data)
        liquidity_score = self._calculate_liquidity_score(vehicle, market_data)
        intelligence_score = self._calculate_intelligence_score(vehicle, value, market_data)
        
        # High demand, high liquidity, good health = SELL NOW
        if demand_score > 80 and liquidity_score > 80 and intelligence_score["overall"] > 75:
            return "Sell Now - Market conditions are optimal"
        
        # Rising market, good condition = HOLD
        trend = market_data.get("demand", {}).get("trend", "0%")
        if "+" in trend and intelligence_score["overall"] > 70:
            return "Hold for 3-6 months - Market is rising"
        
        # Falling market or poor condition = SELL SOON
        if "-" in trend or intelligence_score["overall"] < 60:
            return "Sell Soon - Market conditions are declining"
        
        # Low liquidity = REPAIR FIRST
        if liquidity_score < 50:
            return "Consider minor repairs before selling"
        
        # Default
        return "Monitor market - Values are stable"
    
    def _calculate_holding_period(self, vehicle: VehicleData, market_data: Dict) -> str:
        """Calculate recommended holding period"""
        trend = market_data.get("demand", {}).get("trend", "0%")
        
        if "+" in trend:
            percentage = float(trend.replace("+", "").replace("%", ""))
            if percentage > 5:
                return "6-12 months (market rising fast)"
            else:
                return "3-6 months (market gradually rising)"
        elif "-" in trend:
            return "0-3 months (market declining)"
        else:
            return "3-6 months (market stable)"
    
    def _get_market_trend(self, vehicle: VehicleData, market_data: Dict) -> MarketTrend:
        """Get market trend information"""
        trend_data = market_data.get("demand", {})
        trend_text = trend_data.get("trend", "0%")
        
        if "+" in trend_text:
            trend_type = "Rising"
            percentage = float(trend_text.replace("+", "").replace("%", ""))
        elif "-" in trend_text:
            trend_type = "Falling"
            percentage = float(trend_text.replace("-", "").replace("%", ""))
        else:
            trend_type = "Stable"
            percentage = 0.0
        
        factors = [
            "Market demand",
            "Inventory levels",
            "Economic conditions",
            "Fuel prices",
            "Import regulations"
        ]
        
        return MarketTrend(
            trend=trend_type,
            percentage=percentage,
            timeframe="Last 30 days",
            factors=factors[:3]
        )

# ─── COMPARABLE VEHICLES ENGINE ────────────────────────────────────

class ComparableVehiclesEngine:
    """Find comparable vehicles for valuation"""
    
    def __init__(self):
        # In production, this would query a database
        self.comparable_data = self._load_comparable_data()
    
    def _load_comparable_data(self) -> Dict[str, Any]:
        """Load comparable vehicle data from database"""
        # Sample comparable data
        return {
            "Toyota Corolla 2020": [
                {"make": "Toyota", "model": "Corolla", "year": 2020, "price": 1710000, "source": "Dealer", "mileage": 45000, "condition": "Good"},
                {"make": "Toyota", "model": "Corolla", "year": 2020, "price": 1650000, "source": "Private", "mileage": 52000, "condition": "Good"},
                {"make": "Toyota", "model": "Corolla", "year": 2021, "price": 1800000, "source": "Dealer", "mileage": 28000, "condition": "Excellent"},
            ]
        }
    
    def get_comparables(self, make: str, model: str, year: int) -> List[ComparableVehicle]:
        """Get comparable vehicles"""
        key = f"{make} {model} {year}"
        data = self.comparable_data.get(key, [])
        
        if not data:
            # Try with just make and model
            key = f"{make} {model}"
            data = self.comparable_data.get(key, [])
        
        return [ComparableVehicle(**item) for item in data[:5]]

# ─── API ENDPOINTS ──────────────────────────────────────────────────

@router.get("/service-fee", response_model=ServiceFeeResponse)
async def get_service_fee():
    """Get the current service fee for instant valuation"""
    fee = 500
    if settings.ENV == "production":
        fee = 500
    else:
        fee = 100
    
    return ServiceFeeResponse(
        fee=fee,
        breakdown={
            "valuation": 400,
            "certificate": 50,
            "market_data": 50
        }
    )

@router.post("/valuate", response_model=ValuationResponse)
async def valuate_vehicle(
    request: ValuationRequest,
    authorization: Optional[str] = Header(None)
):
    """Process vehicle valuation with commercial-grade engine"""
    
    try:
        # Validate authentication
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization required")
        
        # Initialize valuation engine
        engine = CommercialValuationEngine()
        comparables_engine = ComparableVehiclesEngine()
        
        # Calculate valuation
        result = engine.calculate_value(request.vehicle)
        
        # Get comparables if requested
        comparables = None
        if request.include_comparables:
            comparables = comparables_engine.get_comparables(
                request.vehicle.make,
                request.vehicle.model,
                request.vehicle.year
            )
        
        # Generate certificate number
        cert_number = f"AUTO-VAL-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
        
        # Generate QR code
        qr_data = {
            "certificate": cert_number,
            "make": request.vehicle.make,
            "model": request.vehicle.model,
            "year": request.vehicle.year,
            "value": result["market_value"],
            "date": datetime.now().isoformat()
        }
        qr_code = hashlib.sha256(json.dumps(qr_data).encode()).hexdigest()[:16]
        
        # Store in database
        await store_valuation(request, result, cert_number)
        
        # Process M-Pesa payment
        transaction_id = None
        # if request.phone:
        #     transaction_id = await process_payment(request.phone, 500)
        
        # Build AI explanation
        ai_explanation = None
        if request.include_ai_explanation and result.get("ai_explanation"):
            exp = result["ai_explanation"]
            ai_explanation = AIExplanation(
                positives=exp.get("positives", []),
                negatives=exp.get("negatives", []),
                summary=exp.get("summary", "")
            )
        
        return ValuationResponse(
            market_value=result["market_value"],
            price_range=result["price_range"],
            confidence_score=result["confidence_score"],
            market_trend=result.get("market_trend"),
            comparables=comparables,
            demand_score=result["demand_score"],
            liquidity_score=result["liquidity_score"],
            intelligence_score=VehicleIntelligenceScore(**result["intelligence_score"]),
            ai_explanation=ai_explanation,
            recommendation=result["recommendation"],
            holding_period=result.get("holding_period"),
            certificate_number=cert_number,
            valuation_date=datetime.now().isoformat(),
            transaction_id=transaction_id,
            qr_code=qr_code
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
        "trim": request.vehicle.trim,
        "grade": request.vehicle.grade.value if request.vehicle.grade else None,
        "engine_capacity": request.vehicle.engine_capacity,
        "fuel_type": request.vehicle.fuel_type.value,
        "transmission": request.vehicle.transmission.value,
        "body_type": request.vehicle.body_type,
        "mileage": request.vehicle.mileage,
        "condition": request.vehicle.condition.value,
        "accident_history": request.vehicle.accident_history.value,
        "location": request.vehicle.location,
        "previous_owners": request.vehicle.previous_owners,
        "usage_type": request.vehicle.usage_type.value,
        "market_value": result["market_value"],
        "confidence_score": result["confidence_score"],
        "demand_score": result["demand_score"],
        "liquidity_score": result["liquidity_score"],
        "intelligence_score": result["intelligence_score"],
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
    return f"TXN-{random.randint(100000, 999999)}"
