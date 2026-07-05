# backend/app/api/v1/endpoints/inspections.py
# =============================================================================
# Inspection Endpoints
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import get_db
from app.models.inspection import Inspection
from app.models.vehicle import Vehicle
from app.models.user import User
from app.api.v1.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class InspectionRequest(BaseModel):
    """Request model for creating an inspection."""
    registration_number: str
    make: str
    model: str
    year: int
    vin: Optional[str] = None
    odometer: int = 0
    body_type: Optional[str] = None
    engine_cc: Optional[int] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    inspection_type: str = "Premium"
    purpose: str = "Pre-Purchase"
    region: str = "Nairobi"
    inspector_name: str
    inspector_credentials: str
    inspector_signature: str
    engine_rating: Optional[str] = "Good"
    transmission_rating: Optional[str] = "Good"
    suspension_rating: Optional[str] = "Good"
    brakes_rating: Optional[str] = "Good"
    paint_rating: Optional[str] = "Good"
    chassis_rating: Optional[str] = "Good"
    interior_rating: Optional[str] = "Good"
    electronics_rating: Optional[str] = "Good"
    tyre_depth_mm: Optional[float] = 6.0
    accident_history: Optional[str] = "None"
    kebs: Optional[Dict[str, Any]] = None

class InspectionResponse(BaseModel):
    """Response model for inspection."""
    id: str
    user_id: str
    vehicle_id: Optional[str]
    registration_number: str
    make: str
    model: str
    year: int
    vin: Optional[str]
    odometer: int
    inspection_type: str
    purpose: str
    region: str
    inspector_name: str
    inspector_credentials: str
    inspector_signature: str
    condition_scores: Dict[str, float]
    issues: List[str]
    kebs_score: Optional[float]
    kebs_status: Optional[str]
    kebs_critical_failures: List[str]
    kebs_results: Dict[str, str]
    overall_score: float
    confidence_score: float
    certificate_number: str
    status: str
    created_at: datetime


# =============================================================================
# Inspection Engine
# =============================================================================

class InspectionEngine:
    """AI-powered inspection scoring engine."""
    
    @staticmethod
    def calculate_scores(data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate inspection scores."""
        rating_map = {'Excellent': 10, 'Good': 8, 'Fair': 5, 'Poor': 3}
        
        engine_score = rating_map.get(data.get('engine_rating', 'Good'), 8)
        transmission_score = rating_map.get(data.get('transmission_rating', 'Good'), 8)
        suspension_score = rating_map.get(data.get('suspension_rating', 'Good'), 8)
        brakes_score = rating_map.get(data.get('brakes_rating', 'Good'), 8)
        paint_score = rating_map.get(data.get('paint_rating', 'Good'), 8)
        chassis_score = rating_map.get(data.get('chassis_rating', 'Good'), 8)
        interior_score = rating_map.get(data.get('interior_rating', 'Good'), 8)
        electronics_score = rating_map.get(data.get('electronics_rating', 'Good'), 8)
        
        tyre_depth = data.get('tyre_depth_mm', 6.0)
        tyre_score = min(10, tyre_depth / 1.6)
        
        accident = data.get('accident_history', 'None')
        accident_factors = {'None': 1.0, 'Minor': 0.9, 'Moderate': 0.7, 'Major': 0.5}
        accident_score = accident_factors.get(accident, 1.0)
        
        # Calculate category scores
        exterior = (paint_score + chassis_score) / 2
        mechanical = (engine_score + transmission_score + suspension_score + brakes_score) / 4
        safety = (brakes_score + tyre_score + (accident_score * 10)) / 3
        interior = interior_score
        electrical = electronics_score
        
        # Overall score
        overall = (exterior + mechanical + safety + interior + electrical) / 5
        overall = overall * accident_score
        
        # Issues detection
        issues = []
        if exterior < 6:
            issues.append("Exterior condition below average")
        if mechanical < 6:
            issues.append("Mechanical components need attention")
        if safety < 6:
            issues.append("Safety features may be compromised")
        if accident != 'None':
            issues.append(f"Accident history: {accident} damage reported")
        if tyre_depth < 4:
            issues.append("Tyres are worn; recommended replacement")
        
        # Confidence score
        confidence = 85 + (5 if all([data.get('engine_rating'), data.get('transmission_rating')]) else 0)
        confidence += (5 if data.get('tyre_depth_mm', 0) > 0 else 0)
        confidence += (5 if data.get('vin') else 0)
        confidence = min(99, confidence)
        
        return {
            'exterior': round(exterior, 1),
            'mechanical': round(mechanical, 1),
            'safety': round(safety, 1),
            'interior': round(interior, 1),
            'electrical': round(electrical, 1),
            'overall': round(overall, 1),
            'issues': issues,
            'confidence_score': confidence
        }


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/inspections", response_model=InspectionResponse)
async def create_inspection(
    request: InspectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new vehicle inspection.
    """
    try:
        # Generate certificate number
        cert_number = f"INS-{datetime.now().strftime('%Y%m')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Calculate scores
        inspection_data = {
            'engine_rating': request.engine_rating,
            'transmission_rating': request.transmission_rating,
            'suspension_rating': request.suspension_rating,
            'brakes_rating': request.brakes_rating,
            'paint_rating': request.paint_rating,
            'chassis_rating': request.chassis_rating,
            'interior_rating': request.interior_rating,
            'electronics_rating': request.electronics_rating,
            'tyre_depth_mm': request.tyre_depth_mm,
            'accident_history': request.accident_history,
            'vin': request.vin
        }
        
        scores = InspectionEngine.calculate_scores(inspection_data)
        
        # Process KEBS results
        kebs_data = request.kebs or {}
        kebs_results = kebs_data.get('results', {})
        kebs_critical_failures = kebs_data.get('criticalFailures', [])
        
        # Create inspection record
        inspection = Inspection(
            user_id=current_user.id,
            registration_number=request.registration_number,
            make=request.make,
            model=request.model,
            year=request.year,
            vin=request.vin,
            odometer=request.odometer,
            inspection_type=request.inspection_type,
            purpose=request.purpose,
            region=request.region,
            inspector_name=request.inspector_name,
            inspector_credentials=request.inspector_credentials,
            inspector_signature=request.inspector_signature,
            condition_scores={
                'exterior': scores['exterior'],
                'mechanical': scores['mechanical'],
                'safety': scores['safety'],
                'interior': scores['interior'],
                'electrical': scores['electrical']
            },
            issues=scores['issues'],
            kebs_score=kebs_data.get('percentage', 0),
            kebs_status=kebs_data.get('status', 'PASS'),
            kebs_critical_failures=kebs_critical_failures,
            kebs_results=kebs_results,
            overall_score=scores['overall'],
            confidence_score=scores['confidence_score'],
            certificate_number=cert_number,
            status='completed' if scores['overall'] >= 5 else 'failed'
        )
        
        db.add(inspection)
        await db.commit()
        await db.refresh(inspection)
        
        logger.info(f"✅ Inspection created for user: {current_user.email}")
        
        return InspectionResponse(
            id=str(inspection.id),
            user_id=str(inspection.user_id),
            vehicle_id=str(inspection.vehicle_id) if inspection.vehicle_id else None,
            registration_number=inspection.registration_number,
            make=inspection.make,
            model=inspection.model,
            year=inspection.year,
            vin=inspection.vin,
            odometer=inspection.odometer,
            inspection_type=inspection.inspection_type,
            purpose=inspection.purpose,
            region=inspection.region,
            inspector_name=inspection.inspector_name,
            inspector_credentials=inspection.inspector_credentials,
            inspector_signature=inspection.inspector_signature,
            condition_scores=inspection.condition_scores,
            issues=inspection.issues or [],
            kebs_score=inspection.kebs_score,
            kebs_status=inspection.kebs_status,
            kebs_critical_failures=inspection.kebs_critical_failures or [],
            kebs_results=inspection.kebs_results or {},
            overall_score=inspection.overall_score,
            confidence_score=inspection.confidence_score,
            certificate_number=inspection.certificate_number,
            status=inspection.status,
            created_at=inspection.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Inspection creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create inspection: {str(e)}"
        )


@router.get("/inspections", response_model=List[InspectionResponse])
async def get_inspections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get all inspections for the current user.
    """
    try:
        query = select(Inspection).where(
            Inspection.user_id == current_user.id
        ).order_by(desc(Inspection.created_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        inspections = result.scalars().all()
        
        return [
            InspectionResponse(
                id=str(i.id),
                user_id=str(i.user_id),
                vehicle_id=str(i.vehicle_id) if i.vehicle_id else None,
                registration_number=i.registration_number,
                make=i.make,
                model=i.model,
                year=i.year,
                vin=i.vin,
                odometer=i.odometer,
                inspection_type=i.inspection_type,
                purpose=i.purpose,
                region=i.region,
                inspector_name=i.inspector_name,
                inspector_credentials=i.inspector_credentials,
                inspector_signature=i.inspector_signature,
                condition_scores=i.condition_scores,
                issues=i.issues or [],
                kebs_score=i.kebs_score,
                kebs_status=i.kebs_status,
                kebs_critical_failures=i.kebs_critical_failures or [],
                kebs_results=i.kebs_results or {},
                overall_score=i.overall_score,
                confidence_score=i.confidence_score,
                certificate_number=i.certificate_number,
                status=i.status,
                created_at=i.created_at
            )
            for i in inspections
        ]
        
    except Exception as e:
        logger.error(f"Get inspections error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get inspections: {str(e)}"
        )


@router.get("/inspections/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific inspection by ID.
    """
    try:
        query = select(Inspection).where(
            Inspection.id == inspection_id,
            Inspection.user_id == current_user.id
        )
        result = await db.execute(query)
        inspection = result.scalar_one_or_none()
        
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection not found"
            )
        
        return InspectionResponse(
            id=str(inspection.id),
            user_id=str(inspection.user_id),
            vehicle_id=str(inspection.vehicle_id) if inspection.vehicle_id else None,
            registration_number=inspection.registration_number,
            make=inspection.make,
            model=inspection.model,
            year=inspection.year,
            vin=inspection.vin,
            odometer=inspection.odometer,
            inspection_type=inspection.inspection_type,
            purpose=inspection.purpose,
            region=inspection.region,
            inspector_name=inspection.inspector_name,
            inspector_credentials=inspection.inspector_credentials,
            inspector_signature=inspection.inspector_signature,
            condition_scores=inspection.condition_scores,
            issues=inspection.issues or [],
            kebs_score=inspection.kebs_score,
            kebs_status=inspection.kebs_status,
            kebs_critical_failures=inspection.kebs_critical_failures or [],
            kebs_results=inspection.kebs_results or {},
            overall_score=inspection.overall_score,
            confidence_score=inspection.confidence_score,
            certificate_number=inspection.certificate_number,
            status=inspection.status,
            created_at=inspection.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get inspection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get inspection: {str(e)}"
        )


@router.delete("/inspections/{inspection_id}")
async def delete_inspection(
    inspection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an inspection.
    """
    try:
        query = select(Inspection).where(
            Inspection.id == inspection_id,
            Inspection.user_id == current_user.id
        )
        result = await db.execute(query)
        inspection = result.scalar_one_or_none()
        
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection not found"
            )
        
        await db.delete(inspection)
        await db.commit()
        
        logger.info(f"✅ Inspection deleted: {inspection_id}")
        return {"message": "Inspection deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete inspection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete inspection: {str(e)}"
        )
