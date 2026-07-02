"""
Inspection Routes - FastAPI Backend
Vehicle inspection creation, retrieval, and quick estimates
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging
import re

from app.core.database import execute_query, get_db
from app.core.dependencies import get_current_user, get_current_active_user, require_role
from app.services.inspection import (
    calculate_inspection,
    get_inspection_price,
    validate_inspection_data,
    quick_inspection
)
from app.services.carapi_service import get_carapi_service
from app.services.vin_validator import vin_validator
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors
from app.models.inspection import (
    InspectorData,
    VehicleInspectionData,
    CreateInspectionRequest,
    QuickEstimateRequest,
    InspectionResponse,
    InspectionListResponse,
    InspectionPriceResponse,
    InspectionStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inspections", tags=["Inspections"])

# ─── Constants ──────────────────────────────────────────────────

INSPECTION_TYPES = ["Standard", "Premium", "Express", "Comprehensive"]
INSPECTION_PURPOSES = ["Pre-Purchase", "Insurance", "Lease", "Certification", "Auction", "Export", "Fleet"]
INSPECTION_REGIONS = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "National", "International"]

# ─── Helper Functions ──────────────────────────────────────────

def generate_certificate_number() -> str:
    """Generate a unique certificate number."""
    return f"INS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()

def build_inspection_query(user_id: str, filters: Dict[str, Any] = None):
    """Build inspection query with filters."""
    query = """
        SELECT * FROM service_requests 
        WHERE user_id = $1 AND service_type = 'inspection'
    """
    params = [user_id]
    param_count = 1
    
    if filters:
        if filters.get('status'):
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(filters['status'])
        
        if filters.get('inspection_type'):
            param_count += 1
            query += f" AND inspection_type = ${param_count}"
            params.append(filters['inspection_type'])
        
        if filters.get('purpose'):
            param_count += 1
            query += f" AND purpose = ${param_count}"
            params.append(filters['purpose'])
        
        if filters.get('make'):
            param_count += 1
            query += f" AND make ILIKE $${param_count}"
            params.append(f"%{filters['make']}%")
        
        if filters.get('registration_number'):
            param_count += 1
            query += f" AND registration_number ILIKE $${param_count}"
            params.append(f"%{filters['registration_number']}%")
        
        if filters.get('date_from'):
            param_count += 1
            query += f" AND created_at >= $${param_count}"
            params.append(filters['date_from'])
        
        if filters.get('date_to'):
            param_count += 1
            query += f" AND created_at <= $${param_count}"
            params.append(filters['date_to'])
    
    query += " ORDER BY created_at DESC"
    
    return query, params

# ─── Routes ──────────────────────────────────────────────────

@router.post("/", response_model=InspectionResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def create_inspection(
    request: CreateInspectionRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Create a new vehicle inspection.
    
    **Request Body:**
    - `vehicle_data`: Vehicle details (make, model, year, vin, etc.)
    - `inspection_type`: Type of inspection (Standard, Premium, Express, Comprehensive)
    - `purpose`: Purpose of inspection (Pre-Purchase, Insurance, Lease, Certification, Auction, Export, Fleet)
    - `region`: Region (Nairobi, Mombasa, Kisumu, Nakuru, Eldoret, National, International)
    - `inspector`: Inspector details
    - `image_urls`: Image URLs
    - `document_urls`: Document URLs
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Inspection record
    - `inspection`: Inspection results
    """
    try:
        vehicle_data = request.vehicle_data.dict()
        
        # If VIN provided, try to auto-fill
        vin = vehicle_data.get('vin')
        if vin:
            vin = vin.upper().strip()
            if vin_validator.is_valid(vin):
                try:
                    carapi = get_carapi_service()
                    vin_data = carapi.decode_vin(vin)
                    if 'error' not in vin_data:
                        vehicle_data['make'] = vin_data.get('make', vehicle_data.get('make'))
                        vehicle_data['model'] = vin_data.get('model', vehicle_data.get('model'))
                        vehicle_data['year'] = vin_data.get('year', vehicle_data.get('year'))
                except Exception as e:
                    logger.warning(f"CarAPI lookup failed: {str(e)}")
        
        # Validate required fields
        required = ['make', 'model', 'year']
        for field in required:
            if not vehicle_data.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing field: {field}"
                )
        
        # Validate data
        is_valid, error = validate_inspection_data(vehicle_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Get inspector from data or use default
        inspector_data = request.inspector.dict() if request.inspector else {}
        if not inspector_data.get('name'):
            inspector_data = {
                'name': current_user.get('full_name', current_user.get('email', 'Unknown')),
                'credentials': 'AUTO-V-System',
                'signature': current_user.get('email', 'Unknown'),
                'license_number': 'AUTO-V-System'
            }
        
        # Get inspection parameters
        inspection_type = request.inspection_type or 'Premium'
        purpose = request.purpose or 'Pre-Purchase'
        region = request.region or 'Nairobi'
        
        # Calculate inspection
        try:
            result = calculate_inspection(
                make=vehicle_data.get('make'),
                model=vehicle_data.get('model'),
                year=int(vehicle_data.get('year', 0)),
                odometer=int(vehicle_data.get('odometer', 0)),
                engine_rating=vehicle_data.get('engine_rating', 'Good'),
                transmission_rating=vehicle_data.get('transmission_rating', 'Good'),
                suspension_rating=vehicle_data.get('suspension_rating', 'Good'),
                brakes_rating=vehicle_data.get('brakes_rating', 'Good'),
                paint_rating=vehicle_data.get('paint_rating', 'Good'),
                chassis_rating=vehicle_data.get('chassis_rating', 'Good'),
                interior_rating=vehicle_data.get('interior_rating', 'Good'),
                electronics_rating=vehicle_data.get('electronics_rating', 'Good'),
                tyre_depth_mm=float(vehicle_data.get('tyre_depth_mm', 6.0)),
                accident_history=vehicle_data.get('accident_history', 'none'),
                inspector_name=inspector_data.get('name'),
                inspector_credentials=inspector_data.get('credentials'),
                inspector_signature=inspector_data.get('signature'),
                inspection_type=inspection_type,
                region=region,
                purpose=purpose,
                inspector=inspector_data
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid numeric value: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Inspection calculation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Inspection calculation failed"
            )
        
        # Generate certificate number
        certificate_number = generate_certificate_number()
        result['certificate_number'] = certificate_number
        result['user_id'] = current_user['id']
        
        # Prepare data for insertion
        insert_data = {
            'user_id': current_user['id'],
            'service_type': 'inspection',
            'registration_number': vehicle_data.get('registration_number'),
            'vin': vehicle_data.get('vin'),
            'make': vehicle_data.get('make'),
            'model': vehicle_data.get('model'),
            'year': vehicle_data.get('year'),
            'odometer': vehicle_data.get('odometer'),
            'condition': vehicle_data.get('condition', 'Good'),
            'accident_history': vehicle_data.get('accident_history', 'None'),
            'inspection_type': inspection_type,
            'purpose': purpose,
            'region': region,
            'amount': get_inspection_price(purpose),
            'payment_status': 'paid',
            'status': 'completed',
            'result': result,
            'inspector': inspector_data,
            'image_urls': request.image_urls or {},
            'document_urls': request.document_urls or {},
            'created_at': format_timestamp(),
            'updated_at': format_timestamp()
        }
        
        # Insert into database
        columns = ', '.join(insert_data.keys())
        placeholders = ', '.join([f'${i+1}' for i in range(len(insert_data))])
        values = list(insert_data.values())
        
        query = f"""
            INSERT INTO service_requests ({columns}) 
            VALUES ({placeholders}) 
            RETURNING id, created_at
        """
        
        db_result = await execute_query(query, values)
        
        if not db_result or len(db_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save inspection"
            )
        
        inspection_record = db_result[0]
        insert_data['id'] = inspection_record['id']
        insert_data['created_at'] = inspection_record['created_at']
        
        return InspectionResponse(
            success=True,
            data=insert_data,
            inspection=result,
            message="Inspection created successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create inspection error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create inspection: {str(e)}"
        )


@router.get("/{inspection_id}", response_model=InspectionResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_inspection(
    inspection_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get inspection by ID.
    
    **Path Parameter:**
    - `inspection_id`: Inspection ID to retrieve
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Inspection data
    """
    try:
        # Query inspection from database
        query = """
            SELECT * FROM service_requests 
            WHERE id = $1 AND service_type = 'inspection'
        """
        
        result = await execute_query(query, [inspection_id])
        
        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection not found"
            )
        
        inspection = result[0]
        
        # Check permissions
        if inspection['user_id'] != current_user['id'] and current_user['role'] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return InspectionResponse(
            success=True,
            data=inspection,
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get inspection error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve inspection: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=InspectionListResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_user_inspections(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    inspection_type: Optional[str] = Query(None),
    purpose: Optional[str] = Query(None),
    make: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get all inspections for a user.
    
    **Path Parameter:**
    - `user_id`: User ID
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50, max: 100)
    - `offset`: Number of results to skip (default: 0)
    - `status`: Filter by status
    - `inspection_type`: Filter by inspection type
    - `purpose`: Filter by purpose
    - `make`: Filter by vehicle make
    - `date_from`: Filter from date
    - `date_to`: Filter to date
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of inspections
    - `total`: Total count
    """
    try:
        # Check permissions
        if user_id != current_user['id'] and current_user['role'] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Build filters
        filters = {
            'status': status,
            'inspection_type': inspection_type,
            'purpose': purpose,
            'make': make,
            'date_from': date_from,
            'date_to': date_to
        }
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # Get total count
        count_query = """
            SELECT COUNT(*) as total FROM service_requests 
            WHERE user_id = $1 AND service_type = 'inspection'
        """
        count_params = [user_id]
        
        if status:
            count_query += " AND status = $2"
            count_params.append(status)
        if inspection_type:
            count_query += " AND inspection_type = $3"
            count_params.append(inspection_type)
        if purpose:
            count_query += " AND purpose = $4"
            count_params.append(purpose)
        
        count_result = await execute_query(count_query, count_params)
        total = count_result[0]['total'] if count_result else 0
        
        # Get inspections with pagination
        query, params = build_inspection_query(user_id, filters)
        query += f" LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([limit, offset])
        
        result = await execute_query(query, params)
        
        return InspectionListResponse(
            success=True,
            data=result or [],
            total=total,
            limit=limit,
            offset=offset,
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user inspections error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve inspections: {str(e)}"
        )


@router.post("/quick-estimate", response_model=InspectionResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def quick_estimate(
    request: QuickEstimateRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Quick inspection estimate.
    
    **Request Body:**
    - `make`: Vehicle make
    - `model`: Vehicle model
    - `year`: Vehicle year
    - `odometer`: Vehicle odometer (optional)
    - `condition`: Vehicle condition (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Quick estimate results
    """
    try:
        # Validate required fields
        if not request.make or not request.model or not request.year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Make, model, and year are required"
            )
        
        # Calculate quick estimate
        result = quick_inspection(
            make=request.make,
            model=request.model,
            year=request.year,
            odometer=request.odometer or 0,
            condition=request.condition or 'good'
        )
        
        return InspectionResponse(
            success=True,
            data={
                'overall_score': result.get('overall_score', 0),
                'safety_score': result.get('safety_score', 0),
                'mechanical_score': result.get('mechanical_score', 0),
                'confidence_score': result.get('confidence_score', 0),
                'issues': result.get('issues', [])[:3],
                'estimated_value': result.get('estimated_value', 0)
            },
            message="Quick estimate completed",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick estimate error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate quick estimate: {str(e)}"
        )


@router.get("/stats", response_model=InspectionStatsResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_inspection_stats(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get inspection statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Statistics (total, completed, pending, avg_score, by_type, by_purpose)
    """
    try:
        # Get all inspections for user
        query = """
            SELECT * FROM service_requests 
            WHERE user_id = $1 AND service_type = 'inspection'
        """
        
        result = await execute_query(query, [current_user['id']])
        inspections = result or []
        
        total = len(inspections)
        completed = len([r for r in inspections if r.get('status') == 'completed'])
        pending = len([r for r in inspections if r.get('status') == 'pending'])
        processing = len([r for r in inspections if r.get('status') == 'processing'])
        failed = len([r for r in inspections if r.get('status') == 'failed'])
        
        # Calculate average score from results
        total_score = 0
        score_count = 0
        by_type = {}
        by_purpose = {}
        
        for r in inspections:
            # By type
            insp_type = r.get('inspection_type', 'Unknown')
            by_type[insp_type] = by_type.get(insp_type, 0) + 1
            
            # By purpose
            purpose = r.get('purpose', 'Unknown')
            by_purpose[purpose] = by_purpose.get(purpose, 0) + 1
            
            # Scores
            result_data = r.get('result', {})
            if result_data.get('overall_score'):
                total_score += result_data.get('overall_score', 0)
                score_count += 1
        
        avg_score = round(total_score / score_count, 1) if score_count > 0 else 0
        
        return InspectionStatsResponse(
            success=True,
            data={
                'total': total,
                'completed': completed,
                'pending': pending,
                'processing': processing,
                'failed': failed,
                'avg_score': avg_score,
                'by_type': by_type,
                'by_purpose': by_purpose
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Inspection stats error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get inspection stats: {str(e)}"
        )


@router.get("/prices", response_model=InspectionPriceResponse)
@rate_limit(limit=20, per=60)
@log_request
@handle_errors
async def get_inspection_prices():
    """
    Get inspection prices.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Price list by purpose
    """
    try:
        prices = {
            "Pre-Purchase": get_inspection_price("Pre-Purchase"),
            "Insurance": get_inspection_price("Insurance"),
            "Lease": get_inspection_price("Lease"),
            "Certification": get_inspection_price("Certification"),
            "Auction": get_inspection_price("Auction"),
            "Export": get_inspection_price("Export"),
            "Fleet": get_inspection_price("Fleet")
        }
        
        return InspectionPriceResponse(
            success=True,
            data=prices,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Inspection prices error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get inspection prices: {str(e)}"
        )


@router.delete("/{inspection_id}", response_model=InspectionResponse)
@rate_limit(limit=5, per=60)
@require_auth
@log_request
@handle_errors
async def delete_inspection(
    inspection_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Delete inspection.
    
    **Path Parameter:**
    - `inspection_id`: Inspection ID to delete
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Status message
    """
    try:
        # Check if inspection exists
        check_query = """
            SELECT * FROM service_requests 
            WHERE id = $1 AND service_type = 'inspection'
        """
        check_result = await execute_query(check_query, [inspection_id])
        
        if not check_result or len(check_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection not found"
            )
        
        inspection = check_result[0]
        
        # Check permissions
        if inspection['user_id'] != current_user['id'] and current_user['role'] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete inspection
        delete_query = """
            DELETE FROM service_requests 
            WHERE id = $1 AND service_type = 'inspection'
        """
        
        await execute_query(delete_query, [inspection_id])
        
        return InspectionResponse(
            success=True,
            message="Inspection deleted successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete inspection error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete inspection: {str(e)}"
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
