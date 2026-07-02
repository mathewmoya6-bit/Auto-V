"""
Assessment Routes - FastAPI Backend
Vehicle assessment, damage analysis, and risk evaluation
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging
import re

from app.core.database import get_db, execute_query
from app.core.dependencies import get_current_user, get_current_active_user, require_role
from app.services.assessment import run_assessment
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors
from app.models.assessment import (
    AssessmentCreate, 
    AssessmentUpdate, 
    AssessmentResponse, 
    AssessmentListResponse,
    AssessmentType,
    QuickAssessmentRequest,
    QuickAssessmentResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assessments", tags=["Assessments"])

# ─── Constants ──────────────────────────────────────────────────

ASSESSMENT_TYPES = {
    "damage": {"name": "Damage Assessment", "description": "Assess vehicle damage and repair costs"},
    "risk": {"name": "Risk Assessment", "description": "Evaluate vehicle risk factors"},
    "condition": {"name": "Condition Assessment", "description": "Assess overall vehicle condition"},
    "value": {"name": "Value Assessment", "description": "Assess vehicle market value"},
    "safety": {"name": "Safety Assessment", "description": "Evaluate vehicle safety features"},
    "theft": {"name": "Theft Risk Assessment", "description": "Assess theft risk factors"},
    "insurance": {"name": "Insurance Risk Assessment", "description": "Evaluate insurance risk factors"},
    "comprehensive": {"name": "Comprehensive Assessment", "description": "Full vehicle assessment"}
}

ASSESSMENT_STATUSES = ["pending", "processing", "completed", "failed", "cancelled"]

# ─── Helper Functions ──────────────────────────────────────────

def generate_assessment_id() -> str:
    """Generate a unique assessment ID."""
    return f"ASS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

def validate_assessment_type(assessment_type: str) -> bool:
    """Validate assessment type."""
    return assessment_type in ASSESSMENT_TYPES

def validate_status(status: str) -> bool:
    """Validate assessment status."""
    return status in ASSESSMENT_STATUSES

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()

def build_assessment_query(user_id: str, filters: Dict[str, Any] = None):
    """Build assessment query with filters."""
    query = "SELECT * FROM assessments WHERE user_id = $1"
    params = [user_id]
    param_count = 1
    
    if filters:
        if filters.get('assessment_type'):
            param_count += 1
            query += f" AND assessment_type = ${param_count}"
            params.append(filters['assessment_type'])
        
        if filters.get('status'):
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(filters['status'])
        
        if filters.get('vehicle_make'):
            param_count += 1
            query += f" AND vehicle_data->>'make' ILIKE $${param_count}"
            params.append(f"%{filters['vehicle_make']}%")
        
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

@router.post("/create", response_model=AssessmentResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def create_assessment(
    request: AssessmentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Create a new vehicle assessment.
    
    **Request Body:**
    - `assessment_type`: Type of assessment (damage, risk, condition, value, safety, theft, insurance, comprehensive)
    - `vehicle`: Vehicle data (make, model, year, vin, etc.)
    - `notes`: Additional notes
    - `images`: List of image URLs
    - `documents`: List of document URLs
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Assessment results
    - `assessment_id`: Unique assessment ID
    - `message`: Status message
    """
    try:
        # Validate assessment type
        if not validate_assessment_type(request.assessment_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid assessment type. Must be one of: {', '.join(ASSESSMENT_TYPES.keys())}"
            )
        
        # Generate assessment ID
        assessment_id = generate_assessment_id()
        
        # Get vehicle data as dict
        vehicle_data = request.vehicle.dict()
        
        # Run assessment
        result = run_assessment(request.assessment_type, vehicle_data)
        
        # Prepare data for insertion
        insert_data = {
            "assessment_id": assessment_id,
            "user_id": current_user['id'],
            "assessment_type": request.assessment_type,
            "vehicle_data": vehicle_data,
            "result": result,
            "notes": request.notes,
            "images": request.images or [],
            "documents": request.documents or [],
            "status": "completed",
            "created_at": format_timestamp(),
            "updated_at": format_timestamp()
        }
        
        # Insert into database
        columns = ', '.join(insert_data.keys())
        placeholders = ', '.join([f'${i+1}' for i in range(len(insert_data))])
        values = list(insert_data.values())
        
        query = f"""
            INSERT INTO assessments ({columns}) 
            VALUES ({placeholders}) 
            RETURNING id, assessment_id, created_at
        """
        
        db_result = await execute_query(query, values)
        
        if not db_result or len(db_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save assessment"
            )
        
        assessment_record = db_result[0]
        
        return AssessmentResponse(
            success=True,
            data=result,
            assessment_id=assessment_id,
            message=f"{ASSESSMENT_TYPES[request.assessment_type]['name']} completed successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create assessment error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create assessment: {str(e)}"
        )


@router.get("/{assessment_id}", response_model=AssessmentResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_assessment(
    assessment_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get assessment by ID.
    
    **Path Parameter:**
    - `assessment_id`: Assessment ID to retrieve
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Assessment data
    """
    try:
        # Query assessment from database
        query = """
            SELECT * FROM assessments 
            WHERE assessment_id = $1
        """
        
        result = await execute_query(query, [assessment_id])
        
        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found"
            )
        
        assessment = result[0]
        
        # Check permissions
        if assessment['user_id'] != current_user['id'] and current_user['role'] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return AssessmentResponse(
            success=True,
            data=assessment,
            assessment_id=assessment['assessment_id'],
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get assessment error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve assessment: {str(e)}"
        )


@router.get("/", response_model=AssessmentListResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def list_assessments(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    assessment_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    vehicle_make: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    List user assessments.
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50, max: 100)
    - `offset`: Number of results to skip (default: 0)
    - `assessment_type`: Filter by assessment type
    - `status`: Filter by status
    - `vehicle_make`: Filter by vehicle make
    - `date_from`: Filter from date
    - `date_to`: Filter to date
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of assessments
    - `total`: Total count
    """
    try:
        # Build filters
        filters = {}
        if assessment_type:
            filters['assessment_type'] = assessment_type
        if status:
            filters['status'] = status
        if vehicle_make:
            filters['vehicle_make'] = vehicle_make
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        # Get total count
        count_query = """
            SELECT COUNT(*) as total FROM assessments 
            WHERE user_id = $1
        """
        count_params = [current_user['id']]
        
        if assessment_type:
            count_query += " AND assessment_type = $2"
            count_params.append(assessment_type)
        if status:
            count_query += " AND status = $3"
            count_params.append(status)
        
        count_result = await execute_query(count_query, count_params)
        total = count_result[0]['total'] if count_result else 0
        
        # Get assessments with pagination
        query = """
            SELECT * FROM assessments 
            WHERE user_id = $1
        """
        params = [current_user['id']]
        param_idx = 2
        
        if assessment_type:
            query += f" AND assessment_type = ${param_idx}"
            params.append(assessment_type)
            param_idx += 1
        if status:
            query += f" AND status = ${param_idx}"
            params.append(status)
            param_idx += 1
        if vehicle_make:
            query += f" AND vehicle_data->>'make' ILIKE $${param_idx}"
            params.append(f"%{vehicle_make}%")
            param_idx += 1
        if date_from:
            query += f" AND created_at >= $${param_idx}"
            params.append(date_from)
            param_idx += 1
        if date_to:
            query += f" AND created_at <= $${param_idx}"
            params.append(date_to)
            param_idx += 1
        
        query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])
        
        result = await execute_query(query, params)
        
        return AssessmentListResponse(
            success=True,
            data=result or [],
            total=total,
            limit=limit,
            offset=offset,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"List assessments error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list assessments: {str(e)}"
        )


@router.put("/{assessment_id}", response_model=AssessmentResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def update_assessment(
    assessment_id: str,
    update_data: AssessmentUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update assessment.
    
    **Path Parameter:**
    - `assessment_id`: Assessment ID to update
    
    **Request Body:**
    - Any fields to update
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Updated assessment data
    """
    try:
        # Check if assessment exists
        check_query = """
            SELECT * FROM assessments 
            WHERE assessment_id = $1
        """
        check_result = await execute_query(check_query, [assessment_id])
        
        if not check_result or len(check_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found"
            )
        
        assessment = check_result[0]
        
        # Check permissions
        if assessment['user_id'] != current_user['id'] and current_user['role'] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Build update query
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Add updated_at
        update_dict['updated_at'] = format_timestamp()
        
        # Validate status if provided
        if 'status' in update_dict and not validate_status(update_dict['status']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(ASSESSMENT_STATUSES)}"
            )
        
        # Build SET clause
        set_clauses = []
        values = []
        param_idx = 1
        
        for key, value in update_dict.items():
            set_clauses.append(f"{key} = ${param_idx}")
            values.append(value)
            param_idx += 1
        
        # Add assessment_id as last parameter
        values.append(assessment_id)
        
        update_query = f"""
            UPDATE assessments 
            SET {', '.join(set_clauses)} 
            WHERE assessment_id = ${param_idx}
            RETURNING *
        """
        
        result = await execute_query(update_query, values)
        
        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update assessment"
            )
        
        return AssessmentResponse(
            success=True,
            data=result[0],
            assessment_id=assessment_id,
            message="Assessment updated successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update assessment error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update assessment: {str(e)}"
        )


@router.delete("/{assessment_id}", response_model=AssessmentResponse)
@rate_limit(limit=5, per=60)
@require_auth
@log_request
@handle_errors
async def delete_assessment(
    assessment_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Delete assessment.
    
    **Path Parameter:**
    - `assessment_id`: Assessment ID to delete
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Status message
    """
    try:
        # Check if assessment exists
        check_query = """
            SELECT * FROM assessments 
            WHERE assessment_id = $1
        """
        check_result = await execute_query(check_query, [assessment_id])
        
        if not check_result or len(check_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found"
            )
        
        assessment = check_result[0]
        
        # Check permissions
        if assessment['user_id'] != current_user['id'] and current_user['role'] not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete assessment
        delete_query = """
            DELETE FROM assessments 
            WHERE assessment_id = $1
        """
        
        await execute_query(delete_query, [assessment_id])
        
        return AssessmentResponse(
            success=True,
            message="Assessment deleted successfully",
            timestamp=format_timestamp()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete assessment error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete assessment: {str(e)}"
        )


@router.get("/types", response_model=AssessmentResponse)
@rate_limit(limit=30, per=60)
@log_request
@handle_errors
async def get_assessment_types():
    """
    Get available assessment types.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of assessment types with descriptions
    """
    return AssessmentResponse(
        success=True,
        data={
            "types": [
                {"key": key, "name": info["name"], "description": info["description"]}
                for key, info in ASSESSMENT_TYPES.items()
            ]
        },
        timestamp=format_timestamp()
    )


@router.post("/quick", response_model=AssessmentResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def quick_assessment(
    request: QuickAssessmentRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Quick vehicle assessment.
    
    **Request Body:**
    - Vehicle data (make, model, year, etc.)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Quick assessment results
    """
    try:
        # Run quick assessment logic
        vehicle = request.vehicle
        
        # Calculate estimated value (simplified)
        base_value = 2000000
        make_factors = {
            "toyota": 1.2,
            "honda": 1.1,
            "mercedes": 1.5,
            "bmw": 1.4,
            "audi": 1.3,
            "nissan": 1.0,
            "ford": 1.0,
            "volkswagen": 1.1
        }
        
        make_factor = make_factors.get(vehicle.make.lower(), 1.0)
        
        # Adjust for year
        current_year = datetime.now().year
        year_factor = 1 - ((current_year - (vehicle.year or current_year)) * 0.08)
        year_factor = max(0.3, year_factor)
        
        # Adjust for mileage
        mileage_factor = 1 - ((vehicle.mileage or 0) / 200000 * 0.3)
        mileage_factor = max(0.5, mileage_factor)
        
        estimated_value = base_value * make_factor * year_factor * mileage_factor
        
        # Determine risk level
        risk_level = "Medium"
        if vehicle.condition == "Excellent":
            risk_level = "Low"
        elif vehicle.condition == "Poor":
            risk_level = "High"
        
        result = {
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "condition": vehicle.condition or "Unknown",
            "estimated_value": round(estimated_value / 1000) * 1000,
            "risk_level": risk_level,
            "assessment_date": format_timestamp(),
            "factors_used": {
                "base_value": base_value,
                "make_factor": make_factor,
                "year_factor": year_factor,
                "mileage_factor": mileage_factor
            }
        }
        
        return AssessmentResponse(
            success=True,
            data=result,
            message="Quick assessment completed",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Quick assessment error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform quick assessment: {str(e)}"
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
