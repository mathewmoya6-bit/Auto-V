"""
Valuation Routes - FastAPI Backend
Vehicle valuation creation, retrieval, quick estimates, and statistics
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
from app.services.valuation import calculate_value, get_valuation_price, validate_valuation_data
from app.services.carapi_service import get_carapi_service
from app.services.vin_validator import vin_validator
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors
from app.models.valuation import (
    ValuationVehicleData,
    ValuationRequest,
    ValuationUpdate,
    ValuationResponse,
    ValuationListResponse,
    QuickEstimateRequest,
    ValuationStatsResponse,
    ValuationPriceResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/valuations", tags=["Valuations"])

# ─── Constants ──────────────────────────────────────────────────

VALUATION_PURPOSES = ["market_value", "insurance", "forced_sale", "trade_in", "private_sale", "finance", "lease", "export"]
VALUATION_METHODOLOGIES = ["market_comparison", "cost_approach", "income_approach", "hybrid", "quick_estimate"]

# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()

def generate_certificate_number() -> str:
    """Generate a unique certificate number."""
    return f"VAL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

def get_default_inspector(user: dict) -> Dict[str, Any]:
    """Get default inspector data from user."""
    return {
        "name": user.get("full_name", user.get("email", "Unknown")),
        "credentials": "AUTO-V-System",
        "signature": user.get("email", "Unknown"),
        "license_number": user.get("license_number", "N/A")
    }

def build_valuation_query(user_id: str, filters: Dict[str, Any] = None):
    """Build valuation query with filters."""
    query = """
        SELECT * FROM service_requests 
        WHERE user_id = $1 AND service_type = 'valuation'
    """
    params = [user_id]
    param_count = 1
    
    if filters:
        if filters.get('status'):
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(filters['status'])
        
        if filters.get('purpose'):
            param_count += 1
            query += f" AND valuation_purpose = ${param_count}"
            params.append(filters['purpose'])
        
        if filters.get('make'):
            param_count += 1
            query += f" AND make ILIKE $${param_count}"
            params.append(f"%{filters['make']}%")
        
        if filters.get('model'):
            param_count += 1
            query += f" AND model ILIKE $${param_count}"
            params.append(f"%{filters['model']}%")
        
        if filters.get('registration_number'):
            param_count += 1
            query += f" AND registration_number ILIKE $${param_count}"
            params.append(f"%{filters['registration_number']}%")
        
        if filters.get('vin'):
            param_count += 1
            query += f" AND vin ILIKE $${param_count}"
            params.append(f"%{filters['vin']}%")
        
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

@router.post("/", response_model=ValuationResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def create_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Create a new vehicle valuation.
    
    **Request Body:**
    - `vehicle_data`: Vehicle details (make, model, year, vin, etc.)
    - `purpose`: Valuation purpose (market_value, insurance, forced_sale, etc.)
    - `methodology`: Valuation methodology
    - `inspector`: Inspector details
    - `notes`: Additional notes
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Valuation record
    - `valuation`: Valuation results
    """
    try:
        vehicle_data = request.vehicle_data.dict()
        purpose = request.purpose or "market_value"
        
        # Validate purpose
        if purpose not in VALUATION_PURPOSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid purpose. Must be one of: {', '.join(VALUATION_PURPOSES)}"
            )
        
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
                        vehicle_data['engine_cc'] = vin_data.get('engine_cc', vehicle_data.get('engine_cc'))
                        vehicle_data['fuel_type'] = vin_data.get('fuel_type', vehicle_data.get('fuel_type'))
                        vehicle_data['transmission'] = vin_data.get('transmission', vehicle_data.get('transmission'))
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
        is_valid, error = validate_valuation_data(vehicle_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Get inspector from data or use default
        inspector = request.inspector or get_default_inspector(current_user)
        if not inspector.get('name'):
            inspector = get_default_inspector(current_user)
        
        # Call valuation engine
        try:
            result = calculate_value(
                make=vehicle_data.get('make'),
                model=vehicle_data.get('model'),
                year=int(vehicle_data.get('year', 0)),
                odometer=int(vehicle_data.get('odometer', 0)),
                condition=vehicle_data.get('condition', 'Good'),
                accident_history=vehicle_data.get('accident_history', 'None'),
                service_history=vehicle_data.get('service_history', 'Full'),
                owners=int(vehicle_data.get('owners', 1)),
                usage=vehicle_data.get('usage', 'Personal'),
                import_status=vehicle_data.get('import_status', 'Local'),
                warranty=vehicle_data.get('warranty', 'Expired'),
                modifications=vehicle_data.get('modifications', 'None'),
                region=vehicle_data.get('region', 'Nairobi'),
                purpose=purpose,
                valuation_methodology=request.methodology or 'market_comparison',
                inspector=inspector,
                current_year=datetime.now().year
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid numeric value: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Valuation calculation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Valuation calculation failed"
            )
        
        # Generate certificate number
        certificate_number = generate_certificate_number()
        result['certificate_number'] = certificate_number
        result['user_id'] = current_user['id']
        
        # Prepare request data
        request_data = {
            'user_id': current_user['id'],
            'service_type': 'valuation',
            'registration_number': vehicle_data.get('registration_number'),
            'vin': vehicle_data.get('vin'),
            'make': vehicle_data.get('make'),
            'model': vehicle_data.get('model'),
            'year': vehicle_data.get('year'),
            'odometer': vehicle_data.get('odometer'),
            'condition': vehicle_data.get('condition', 'Good'),
            'accident_history': vehicle_data.get('accident_history', 'None'),
            'valuation_purpose': purpose,
            'valuation_methodology': request.methodology or 'market_comparison',
            'amount': get_valuation_price(purpose),
            'payment_status': 'paid',
            'status': 'completed',
            'result': result,
            'inspector': inspector,
            'notes': request.notes,
            'created_at': format_timestamp(),
            'updated_at': format_timestamp(),
            'completed_at': format_timestamp()
        }
        
        # Insert into database
        columns = ', '.join(request_data.keys())
        placeholders = ', '.join([f'${i+1}' for i in range(len(request_data))])
        values = list(request_data.values())
        
        query = f"""
            INSERT INTO service_requests ({columns}) 
            VALUES ({placeholders}) 
            RETURNING id, created_at
        """
        
        db_result = await execute_query(query, values)
        
        if not db_result or len(db_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save valuation"
            )
        
        valuation_record = db_result[0]
        request_data['id'] = valuation_record['id']
        request_data['created_at'] = valuation_record['created_at']
        
        return ValuationResponse(
            success=True,
            data=request_data,
            valuation=result,
            message="Valuation created successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create valuation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create valuation: {str(e)}"
        )


@router.get("/{valuation_id}", response_model=ValuationResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_valuation(
    valuation_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get valuation by ID.
    
    **Path Parameter:**
    - `valuation_id`: Valuation ID
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Valuation data
    """
    try:
        # Query valuation from database
        query = """
            SELECT * FROM service_requests 
            WHERE id = $1 AND service_type = 'valuation'
        """
        
        result = await execute_query(query, [valuation_id])
        
        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation not found"
            )
        
        valuation = result[0]
        
        # Check permissions
        if valuation['user_id'] != current_user['id'] and current_user['role'] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return ValuationResponse(
            success=True,
            data=valuation,
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get valuation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve valuation: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=ValuationListResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_user_valuations(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    purpose: Optional[str] = Query(None),
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get all valuations for a user.
    
    **Path Parameter:**
    - `user_id`: User ID
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50, max: 100)
    - `offset`: Number of results to skip (default: 0)
    - `status`: Filter by status
    - `purpose`: Filter by purpose
    - `make`: Filter by vehicle make
    - `model`: Filter by vehicle model
    - `date_from`: Filter from date
    - `date_to`: Filter to date
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of valuations
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
            'purpose': purpose,
            'make': make,
            'model': model,
            'date_from': date_from,
            'date_to': date_to
        }
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # Get total count
        count_query = """
            SELECT COUNT(*) as total FROM service_requests 
            WHERE user_id = $1 AND service_type = 'valuation'
        """
        count_params = [user_id]
        
        if status:
            count_query += " AND status = $2"
            count_params.append(status)
        if purpose:
            count_query += " AND valuation_purpose = $3"
            count_params.append(purpose)
        
        count_result = await execute_query(count_query, count_params)
        total = count_result[0]['total'] if count_result else 0
        
        # Get valuations with pagination
        query, params = build_valuation_query(user_id, filters)
        query += f" LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([limit, offset])
        
        result = await execute_query(query, params)
        
        return ValuationListResponse(
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
        logger.error(f"Get user valuations error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve valuations: {str(e)}"
        )


@router.get("/vehicle/{vin}", response_model=ValuationListResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_valuations_by_vin(
    vin: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get valuations for a vehicle by VIN.
    
    **Path Parameter:**
    - `vin`: Vehicle VIN
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of valuations
    - `total`: Total count
    """
    try:
        vin = vin.upper().strip()
        
        # Validate VIN
        if not vin_validator.is_valid(vin):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid VIN format"
            )
        
        # Get valuations from database
        query = """
            SELECT * FROM service_requests 
            WHERE vin = $1 AND service_type = 'valuation'
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        result = await execute_query(query, [vin, limit])
        
        return ValuationListResponse(
            success=True,
            data=result or [],
            total=len(result) if result else 0,
            limit=limit,
            offset=0,
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get valuations by VIN error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve valuations: {str(e)}"
        )


@router.post("/quick-estimate", response_model=ValuationResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def quick_estimate(
    request: QuickEstimateRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Quick valuation estimate (for instant check).
    
    **Request Body:**
    - `make`: Vehicle make
    - `model`: Vehicle model
    - `year`: Vehicle year
    - `odometer`: Vehicle odometer (optional)
    - `condition`: Vehicle condition (optional)
    - `region`: Region (optional)
    
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
        result = calculate_value(
            make=request.make,
            model=request.model,
            year=request.year,
            odometer=request.odometer or 0,
            condition=request.condition or 'Good',
            accident_history='None',
            service_history='Full',
            owners=1,
            usage='Personal',
            import_status='Local',
            warranty='Expired',
            modifications='None',
            region=request.region or 'Nairobi',
            purpose='market_value',
            valuation_methodology='quick_estimate',
            inspector={"name": "AUTO-V-System", "credentials": "Quick Estimate"},
            current_year=datetime.now().year
        )
        
        return ValuationResponse(
            success=True,
            data={
                "market_value": result.get("market_value", 0),
                "insurance_value": result.get("insurance_value", 0),
                "forced_sale_value": result.get("forced_sale_value", 0),
                "trade_in_value": result.get("trade_in_value", 0),
                "confidence_score": result.get("confidence_score", 0),
                "estimated_range": {
                    "low": result.get("market_value", 0) * 0.9,
                    "high": result.get("market_value", 0) * 1.1
                }
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


@router.get("/stats", response_model=ValuationStatsResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_valuation_stats(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get valuation statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Statistics (total, completed, pending, avg_value, by_purpose, by_year)
    """
    try:
        # Get all valuations for user
        query = """
            SELECT * FROM service_requests 
            WHERE user_id = $1 AND service_type = 'valuation'
        """
        
        result = await execute_query(query, [current_user['id']])
        valuations = result or []
        
        total = len(valuations)
        completed = len([r for r in valuations if r.get('status') == 'completed'])
        pending = len([r for r in valuations if r.get('status') == 'pending'])
        processing = len([r for r in valuations if r.get('status') == 'processing'])
        failed = len([r for r in valuations if r.get('status') == 'failed'])
        
        # Calculate average values
        total_value = 0
        value_count = 0
        by_purpose = {}
        by_year = {}
        
        for r in valuations:
            # By purpose
            purpose = r.get('valuation_purpose', 'Unknown')
            by_purpose[purpose] = by_purpose.get(purpose, 0) + 1
            
            # By year
            year = r.get('year', 0)
            if year:
                by_year[str(year)] = by_year.get(str(year), 0) + 1
            
            # Values
            result_data = r.get('result', {})
            if result_data.get('market_value'):
                total_value += result_data.get('market_value', 0)
                value_count += 1
        
        avg_value = total_value / value_count if value_count > 0 else 0
        
        return ValuationStatsResponse(
            success=True,
            data={
                'total': total,
                'completed': completed,
                'pending': pending,
                'processing': processing,
                'failed': failed,
                'avg_value': avg_value,
                'total_value': total_value,
                'by_purpose': by_purpose,
                'by_year': by_year
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Valuation stats error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuation stats: {str(e)}"
        )


@router.get("/prices", response_model=ValuationPriceResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_valuation_prices(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get valuation prices by purpose.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Price list by purpose
    """
    try:
        prices = {
            "market_value": get_valuation_price("market_value"),
            "insurance": get_valuation_price("insurance"),
            "forced_sale": get_valuation_price("forced_sale"),
            "trade_in": get_valuation_price("trade_in"),
            "private_sale": get_valuation_price("private_sale"),
            "finance": get_valuation_price("finance"),
            "lease": get_valuation_price("lease"),
            "export": get_valuation_price("export")
        }
        
        return ValuationPriceResponse(
            success=True,
            data=prices,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get valuation prices error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get valuation prices: {str(e)}"
        )


@router.delete("/{valuation_id}", response_model=ValuationResponse)
@rate_limit(limit=5, per=60)
@require_auth
@log_request
@handle_errors
async def delete_valuation(
    valuation_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Delete valuation.
    
    **Path Parameter:**
    - `valuation_id`: Valuation ID to delete
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Status message
    """
    try:
        # Check if valuation exists
        check_query = """
            SELECT * FROM service_requests 
            WHERE id = $1 AND service_type = 'valuation'
        """
        check_result = await execute_query(check_query, [valuation_id])
        
        if not check_result or len(check_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Valuation not found"
            )
        
        valuation = check_result[0]
        
        # Check permissions
        if valuation['user_id'] != current_user['id'] and current_user['role'] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete valuation
        delete_query = """
            DELETE FROM service_requests 
            WHERE id = $1 AND service_type = 'valuation'
        """
        
        await execute_query(delete_query, [valuation_id])
        
        return ValuationResponse(
            success=True,
            message="Valuation deleted successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete valuation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete valuation: {str(e)}"
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
