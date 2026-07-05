# backend/app/api/v1/endpoints/valuations.py
# =============================================================================
# Valuation Endpoints
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import get_db
from app.models.valuation import Valuation
from app.models.vehicle import Vehicle
from app.models.user import User
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class ValuationRequest(BaseModel):
    """Request model for creating a valuation."""
    vehicle_id: Optional[str] = None
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., ge=1980, le=2026, description="Year of manufacture")
    engine_capacity: Optional[int] = Field(None, description="Engine capacity in cc")
    fuel_type: Optional[str] = Field("Petrol", description="Fuel type")
    transmission: Optional[str] = Field("Automatic", description="Transmission type")
    body_type: Optional[str] = Field(None, description="Body type")
    body_color: Optional[str] = Field(None, description="Body color")
    mileage: Optional[int] = Field(0, description="Odometer reading")
    condition: Optional[str] = Field("Good", description="Vehicle condition")
    accident_history: Optional[str] = Field("None", description="Accident history")
    location: Optional[str] = Field("Nairobi", description="Location")
    previous_owners: Optional[int] = Field(0, description="Number of previous owners")
    usage_type: Optional[str] = Field("Personal", description="Usage type")
    phone: Optional[str] = Field(None, description="Contact phone")

class InstantValuationRequest(BaseModel):
    """Request model for instant valuation."""
    user_id: str
    vehicle: Dict[str, Any]
    phone: Optional[str] = None
    valuation_id: Optional[str] = None

class ValuationResponse(BaseModel):
    """Response model for valuation."""
    id: str
    user_id: str
    vehicle_id: Optional[str]
    make: str
    model: str
    year: int
    engine_capacity: Optional[int]
    fuel_type: Optional[str]
    transmission: Optional[str]
    body_type: Optional[str]
    body_color: Optional[str]
    mileage: Optional[int]
    condition: Optional[str]
    accident_history: Optional[str]
    location: Optional[str]
    previous_owners: Optional[int]
    usage_type: Optional[str]
    market_value: Optional[float]
    insurance_value: Optional[float]
    trade_in_value: Optional[float]
    forced_sale_value: Optional[float]
    confidence_score: Optional[float]
    certificate_number: Optional[str]
    status: str
    created_at: datetime

class ValuationStatsResponse(BaseModel):
    total: float
    average: float
    count: int


# =============================================================================
# AI Valuation Engine (Mock - Replace with actual AI model)
# =============================================================================

class ValuationEngine:
    """AI-powered valuation engine."""
    
    @staticmethod
    def calculate_market_value(data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate market value using AI."""
        # Base value by make and model
        base_values = {
            'Toyota': {'Prado': 5800000, 'Corolla': 3500000, 'Hilux': 4200000, 'Land Cruiser': 8500000, 'RAV4': 4500000},
            'Honda': {'Civic': 3200000, 'Accord': 3800000, 'CR-V': 4000000, 'Fit': 2500000},
            'Nissan': {'X-Trail': 3800000, 'Patrol': 6200000, 'Note': 2200000, 'Qashqai': 3500000},
            'Mercedes': {'C-Class': 5200000, 'E-Class': 6800000, 'GLC': 6000000, 'GLE': 7800000},
            'BMW': {'X5': 6200000, '3 Series': 4800000, '5 Series': 5800000, 'X3': 5200000},
            'Volkswagen': {'Golf': 3000000, 'Polo': 2500000, 'Tiguan': 3800000, 'Passat': 3500000},
            'Ford': {'Focus': 2800000, 'Fiesta': 2200000, 'Ranger': 4000000, 'Explorer': 4500000},
            'Subaru': {'Impreza': 3200000, 'Forester': 3800000, 'Outback': 4000000, 'XV': 3500000},
            'Mazda': {'3': 2800000, '6': 3200000, 'CX-5': 3800000, 'CX-3': 3000000},
            'Mitsubishi': {'Outlander': 3500000, 'Pajero': 4500000, 'Lancer': 2800000, 'ASX': 3000000},
            'Isuzu': {'D-Max': 3800000, 'MU-X': 4200000},
            'Peugeot': {'208': 2200000, '308': 2800000, '508': 3500000, '2008': 3000000},
            'Land Rover': {'Defender': 8500000, 'Discovery': 7200000, 'Range Rover': 12500000, 'Evoque': 5800000},
            'Jaguar': {'XE': 4500000, 'XF': 5200000, 'F-Pace': 5800000, 'E-Pace': 4800000},
            'Lexus': {'IS': 4800000, 'ES': 5200000, 'RX': 6200000, 'NX': 5200000},
            'Volvo': {'S60': 4200000, 'S90': 5200000, 'XC60': 4800000, 'XC90': 6200000},
            'Hyundai': {'i10': 1500000, 'i20': 1800000, 'i30': 2200000, 'Tucson': 3200000, 'Santa Fe': 3800000},
            'Kia': {'Picanto': 1400000, 'Rio': 1600000, 'Cerato': 2200000, 'Sportage': 3200000, 'Sorento': 3800000},
            'Suzuki': {'Swift': 1800000, 'Jimny': 2800000, 'Vitara': 3200000, 'Baleno': 2000000},
        }
        
        make = data.get('make', 'Toyota')
        model = data.get('model', 'Corolla')
        year = data.get('year', 2020)
        mileage = data.get('mileage', 50000)
        condition = data.get('condition', 'Good')
        accident_history = data.get('accident_history', 'None')
        location = data.get('location', 'Nairobi')
        
        # Get base value
        make_models = base_values.get(make, {})
        base_value = make_models.get(model, 3500000)  # Default fallback
        
        # Year adjustment (depreciation)
        current_year = datetime.now().year
        age = current_year - year
        depreciation_per_year = 0.08  # 8% per year
        year_factor = max(0.4, 1 - (age * depreciation_per_year))
        
        # Mileage adjustment
        mileage_factor = max(0.6, 1 - (mileage / 200000 * 0.4))
        
        # Condition adjustment
        condition_factors = {
            'Excellent': 1.15,
            'Good': 1.0,
            'Fair': 0.85,
            'Poor': 0.70
        }
        condition_factor = condition_factors.get(condition, 1.0)
        
        # Accident history adjustment
        accident_factors = {
            'None': 1.0,
            'Minor': 0.90,
            'Major': 0.75,
            'WriteOff': 0.50
        }
        accident_factor = accident_factors.get(accident_history, 1.0)
        
        # Location adjustment
        location_factors = {
            'Nairobi': 1.0,
            'Mombasa': 0.95,
            'Kisumu': 0.92,
            'Nakuru': 0.93,
            'Eldoret': 0.91,
            'Other': 0.88
        }
        location_factor = location_factors.get(location, 0.90)
        
        # Engine capacity adjustment
        engine_capacity = data.get('engine_capacity', 2000)
        if engine_capacity > 3000:
            engine_factor = 1.15
        elif engine_capacity > 2000:
            engine_factor = 1.05
        else:
            engine_factor = 1.0
        
        # Calculate market value
        market_value = base_value * year_factor * mileage_factor * condition_factor * accident_factor * location_factor * engine_factor
        
        # Calculate other values
        insurance_value = market_value * 0.95
        trade_in_value = market_value * 0.85
        forced_sale_value = market_value * 0.70
        
        # Confidence score based on data completeness
        confidence_score = 85 + (5 if all([make, model, year]) else 0)
        confidence_score += (5 if mileage and mileage > 0 else 0)
        confidence_score += (5 if condition != 'Good' else 0)
        confidence_score = min(99, confidence_score)
        
        return {
            'market_value': round(market_value, 2),
            'insurance_value': round(insurance_value, 2),
            'trade_in_value': round(trade_in_value, 2),
            'forced_sale_value': round(forced_sale_value, 2),
            'confidence_score': confidence_score
        }


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/valuations", response_model=ValuationResponse)
async def create_valuation(
    request: ValuationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new vehicle valuation.
    """
    try:
        # Check if vehicle exists and belongs to user
        vehicle = None
        if request.vehicle_id:
            query = select(Vehicle).where(
                Vehicle.id == request.vehicle_id,
                Vehicle.user_id == current_user.id
            )
            result = await db.execute(query)
            vehicle = result.scalar_one_or_none()
            
            if not vehicle:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vehicle not found or does not belong to you"
                )
        
        # Generate certificate number
        cert_number = f"AUTO-VAL-{datetime.now().strftime('%Y%m')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate valuation
        valuation_data = {
            'make': request.make,
            'model': request.model,
            'year': request.year,
            'engine_capacity': request.engine_capacity,
            'fuel_type': request.fuel_type,
            'transmission': request.transmission,
            'body_type': request.body_type,
            'body_color': request.body_color,
            'mileage': request.mileage,
            'condition': request.condition,
            'accident_history': request.accident_history,
            'location': request.location,
            'previous_owners': request.previous_owners,
            'usage_type': request.usage_type
        }
        
        result = ValuationEngine.calculate_market_value(valuation_data)
        
        # Create valuation record
        valuation = Valuation(
            user_id=current_user.id,
            vehicle_id=request.vehicle_id,
            make=request.make,
            model=request.model,
            year=request.year,
            engine_capacity=request.engine_capacity,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            body_type=request.body_type,
            body_color=request.body_color,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            location=request.location,
            previous_owners=request.previous_owners,
            usage_type=request.usage_type,
            market_value=result['market_value'],
            insurance_value=result['insurance_value'],
            trade_in_value=result['trade_in_value'],
            forced_sale_value=result['forced_sale_value'],
            confidence_score=result['confidence_score'],
            certificate_number=cert_number,
            status='completed'
        )
        
        db.add(valuation)
        await db.commit()
        await db.refresh(valuation)
        
        logger.info(f"✅ Valuation created for user: {current_user.email}")
        
        return ValuationResponse(
            id=str(valuation.id),
            user_id=str(valuation.user_id),
            vehicle_id=str(valuation.vehicle_id) if valuation.vehicle_id else None,
            make=valuation.make,
            model=valuation.model,
            year=valuation.year,
            engine_capacity=valuation.engine_capacity,
            fuel_type=valuation.fuel_type,
            transmission=valuation.transmission,
            body_type=valuation.body_type,
            body_color=valuation.body_color,
            mileage=valuation.mileage,
            condition=valuation.condition,
            accident_history=valuation.accident_history,
            location=valuation.location,
            previous_owners=valuation.previous_owners,
            usage_type=valuation.usage_type,
            market_value=valuation.market_value,
            insurance_value=valuation.insurance_value,
            trade_in_value=valuation.trade_in_value,
            forced_sale_value=valuation.forced_sale_value,
            confidence_score=valuation.confidence_score,
            certificate_number=valuation.certificate_number,
            status=valuation.status,
            created_at=valuation.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Valuation creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create valuation: {str(e)}"
        )


@router.post("/valuations/instant")
async def create_instant_valuation(
    request: InstantValuationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create an instant AI valuation.
    """
    try:
        # Get vehicle data from request
        vehicle_data = request.vehicle
        phone = request.phone
        
        # Calculate valuation
        result = ValuationEngine.calculate_market_value(vehicle_data)
        
        # Generate certificate number
        cert_number = f"AUTO-INST-{datetime.now().strftime('%Y%m')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Save valuation if user_id provided
        if request.user_id:
            # Check if user exists
            query = select(User).where(User.id == request.user_id)
            result_query = await db.execute(query)
            user = result_query.scalar_one_or_none()
            
            if user:
                valuation = Valuation(
                    user_id=user.id,
                    make=vehicle_data.get('make'),
                    model=vehicle_data.get('model'),
                    year=vehicle_data.get('year'),
                    engine_capacity=vehicle_data.get('engine_capacity'),
                    fuel_type=vehicle_data.get('fuel_type'),
                    transmission=vehicle_data.get('transmission'),
                    body_type=vehicle_data.get('body_type'),
                    body_color=vehicle_data.get('body_color'),
                    mileage=vehicle_data.get('mileage'),
                    condition=vehicle_data.get('condition'),
                    accident_history=vehicle_data.get('accident_history'),
                    location=vehicle_data.get('location'),
                    previous_owners=vehicle_data.get('previous_owners'),
                    usage_type=vehicle_data.get('usage_type'),
                    market_value=result['market_value'],
                    insurance_value=result['insurance_value'],
                    trade_in_value=result['trade_in_value'],
                    forced_sale_value=result['forced_sale_value'],
                    confidence_score=result['confidence_score'],
                    certificate_number=cert_number,
                    status='completed'
                )
                db.add(valuation)
                await db.commit()
                await db.refresh(valuation)
        
        # Return result
        return {
            'market_value': result['market_value'],
            'insurance_value': result['insurance_value'],
            'trade_in_value': result['trade_in_value'],
            'forced_sale_value': result['forced_sale_value'],
            'confidence_score': result['confidence_score'],
            'certificate_number': cert_number,
            'phone': phone,
            'vehicle': vehicle_data
        }
        
    except Exception as e:
        logger.error(f"Instant valuation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create instant valuation: {str(e)}"
        )


@router.get("/valuations", response_model=List[ValuationResponse])
async def get_valuations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get all valuations for the current user.
    """
    try:
        query = select(Valuation).where(
            Valuation.user_id == current_user.id
        ).order_by(desc(Valuation.created_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        valuations = result.scalars().all()
        
        return [
            ValuationResponse(
                id=str(v.id),
                user_id=str(v.user_id),
                vehicle_id=str(v.vehicle_id) if v.vehicle_id else None,
                make=v.make,
                model=v.model,
                year=v.year,
                engine_capacity=v.engine_capacity,
                fuel_type=v.fuel_type,
                transmission=v.transmission,
                body_type=v.body_type,
                body_color=v.body_color,
                mileage=v.mileage,
                condition=v.condition,
                accident_history=v.accident_history,
                location=v.location,
                previous_owners=v.previous_owners,
                usage_type=v.usage_type,
                market_value=v.market_value,
                insurance_value=v.insurance_value,
                trade_in_value=v.trade_in_value,
                forced_sale_value=v.forced_sale_value,
                confidence_score=v.confidence_score,
                certificate_number=v.certificate_number,
                status=v.status,
                created_at=v.created_at
            )
            for v in valuations
        ]
        
    except Exception as e:
        logger.error(f"Get valuations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuations: {str(e)}"
        )


@router.get("/valuations/{valuation_id}", response_model=ValuationResponse)
async def get_valuation(
    valuation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific valuation by ID.
    """
    try:
        query = select(Valuation).where(
            Valuation.id == valuation_id,
            Valuation.user_id == current_user.id
        )
        result = await db.execute(query)
        valuation = result.scalar_one_or_none()
        
        if not valuation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation not found"
            )
        
        return ValuationResponse(
            id=str(valuation.id),
            user_id=str(valuation.user_id),
            vehicle_id=str(valuation.vehicle_id) if valuation.vehicle_id else None,
            make=valuation.make,
            model=valuation.model,
            year=valuation.year,
            engine_capacity=valuation.engine_capacity,
            fuel_type=valuation.fuel_type,
            transmission=valuation.transmission,
            body_type=valuation.body_type,
            body_color=valuation.body_color,
            mileage=valuation.mileage,
            condition=valuation.condition,
            accident_history=valuation.accident_history,
            location=valuation.location,
            previous_owners=valuation.previous_owners,
            usage_type=valuation.usage_type,
            market_value=valuation.market_value,
            insurance_value=valuation.insurance_value,
            trade_in_value=valuation.trade_in_value,
            forced_sale_value=valuation.forced_sale_value,
            confidence_score=valuation.confidence_score,
            certificate_number=valuation.certificate_number,
            status=valuation.status,
            created_at=valuation.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get valuation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuation: {str(e)}"
        )


@router.get("/valuations/total", response_model=ValuationStatsResponse)
async def get_valuation_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get valuation statistics for the current user.
    """
    try:
        query = select(
            func.sum(Valuation.market_value).label('total'),
            func.avg(Valuation.market_value).label('average'),
            func.count(Valuation.id).label('count')
        ).where(Valuation.user_id == current_user.id)
        
        result = await db.execute(query)
        stats = result.first()
        
        return ValuationStatsResponse(
            total=stats.total or 0,
            average=stats.average or 0,
            count=stats.count or 0
        )
        
    except Exception as e:
        logger.error(f"Get valuation stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuation stats: {str(e)}"
        )


@router.delete("/valuations/{valuation_id}")
async def delete_valuation(
    valuation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a valuation.
    """
    try:
        query = select(Valuation).where(
            Valuation.id == valuation_id,
            Valuation.user_id == current_user.id
        )
        result = await db.execute(query)
        valuation = result.scalar_one_or_none()
        
        if not valuation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation not found"
            )
        
        await db.delete(valuation)
        await db.commit()
        
        logger.info(f"✅ Valuation deleted: {valuation_id}")
        return {"message": "Valuation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete valuation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete valuation: {str(e)}"
        )
