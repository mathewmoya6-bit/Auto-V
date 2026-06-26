"""
Service Routes - FastAPI Version
Service management, creation, and tracking for AUTO-V platform
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import supabase
from app.core.dependencies import get_current_user, get_current_user_optional
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/services", tags=["Services"])


# ─── Pydantic Models ──────────────────────────────────────────

class ServiceBase(BaseModel):
    """Base service model"""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    is_active: bool = True
    estimated_time: Optional[str] = None


class ServiceRequestCreate(BaseModel):
    """Service request creation model"""
    service_type: str = Field(..., description="Type of service")
    vehicle_id: Optional[str] = Field(None, description="Vehicle ID")
    vehicle_data: Optional[Dict[str, Any]] = Field(None, description="Vehicle data")
    customer_type: Optional[str] = Field("individual", description="Customer type")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    customer_email: Optional[str] = Field(None, description="Customer email")
    company_name: Optional[str] = Field(None, description="Company name")
    purpose: Optional[str] = Field(None, description="Service purpose")
    notes: Optional[str] = Field(None, description="Additional notes")
    images: Optional[List[str]] = Field(None, description="Image URLs")
    documents: Optional[List[str]] = Field(None, description="Document URLs")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('service_type')
    def validate_service_type(cls, v):
        valid_types = ['valuation', 'inspection', 'assessment', 'mileage', 'fleet', 'certificate', 'report', 'instant']
        if v not in valid_types:
            raise ValueError(f'Service type must be one of: {", ".join(valid_types)}')
        return v


class ServiceRequestUpdate(BaseModel):
    """Service request update model"""
    status: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None
    inspector: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ServiceRequestResponse(BaseModel):
    """Service request response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    count: Optional[int] = None
    timestamp: Optional[str] = None


# ─── Constants ──────────────────────────────────────────────────

SERVICES = [
    {
        "id": "valuation",
        "name": "Vehicle Valuation",
        "description": "AI-powered vehicle valuation with market analysis",
        "price": 2500,
        "category": "valuation",
        "is_active": True,
        "estimated_time": "5-10 minutes"
    },
    {
        "id": "inspection",
        "name": "Vehicle Inspection",
        "description": "Comprehensive vehicle inspection with damage detection",
        "price": 3500,
        "category": "inspection",
        "is_active": True,
        "estimated_time": "30-45 minutes"
    },
    {
        "id": "assessment",
        "name": "Vehicle Assessment",
        "description": "Detailed vehicle assessment with risk analysis",
        "price": 3000,
        "category": "assessment",
        "is_active": True,
        "estimated_time": "20-30 minutes"
    },
    {
        "id": "mileage",
        "name": "Mileage Rate Report",
        "description": "Cost per kilometre analysis and fuel efficiency report",
        "price": 1500,
        "category": "mileage",
        "is_active": True,
        "estimated_time": "10-15 minutes"
    },
    {
        "id": "fleet",
        "name": "Fleet Services",
        "description": "Complete fleet management and analytics",
        "price": 4000,
        "category": "fleet",
        "is_active": True,
        "estimated_time": "Custom"
    },
    {
        "id": "certificate",
        "name": "Certificate Generation",
        "description": "Generate official AUTO-V certificates",
        "price": 1000,
        "category": "certificate",
        "is_active": True,
        "estimated_time": "5 minutes"
    },
    {
        "id": "report",
        "name": "Custom Report",
        "description": "Custom vehicle intelligence report",
        "price": 2000,
        "category": "report",
        "is_active": True,
        "estimated_time": "15-20 minutes"
    },
    {
        "id": "instant",
        "name": "Instant Value Check",
        "description": "Quick AI-powered vehicle value estimate",
        "price": 500,
        "category": "instant",
        "is_active": True,
        "estimated_time": "Instant"
    }
]


# ─── Helper Functions ──────────────────────────────────────────

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


def generate_request_number() -> str:
    """Generate a unique service request number."""
    return f"SR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def get_service_by_id(service_id: str) -> Optional[Dict[str, Any]]:
    """Get service details by ID."""
    for service in SERVICES:
        if service["id"] == service_id:
            return service
    return None


def validate_service_request_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate service request data."""
    # Check required fields based on service type
    service_type = data.get("service_type")
    
    if service_type in ["valuation", "inspection", "assessment"]:
        # These services require vehicle data
        vehicle_data = data.get("vehicle_data", {})
        if not vehicle_data.get("make") or not vehicle_data.get("model"):
            return False, "Vehicle make and model are required"
        if not vehicle_data.get("year"):
            return False, "Vehicle year is required"
    
    if service_type in ["mileage"]:
        # Mileage service requires vehicle data
        vehicle_data = data.get("vehicle_data", {})
        if not vehicle_data.get("engine_type") or not vehicle_data.get("engine_cc"):
            return False, "Engine type and capacity are required"
        if not data.get("trip_data"):
            return False, "Trip data is required"
    
    return True, None


# ─── Routes ──────────────────────────────────────────────────

@router.get("/", response_model=ServiceRequestResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_services(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all available services.
    
    **Query Parameters:**
    - `category`: Filter by category (optional)
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of services
    - `error`: Error message if unsuccessful
    """
    try:
        services = SERVICES
        
        # Filter by category if provided
        if category:
            services = [s for s in services if s.get("category") == category]
        
        return ServiceRequestResponse(
            success=True,
            data=services,
            count=len(services),
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get services error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


@router.get("/{service_id}", response_model=ServiceRequestResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_service(
    service_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get service details by ID.
    
    **Path Parameter:**
    - `service_id`: Service ID
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Service details
    - `error`: Error message if unsuccessful
    """
    try:
        service = get_service_by_id(service_id)
        
        if not service:
            return ServiceRequestResponse(
                success=False,
                error="Service not found"
            )
        
        return ServiceRequestResponse(
            success=True,
            data=service,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get service error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


@router.post("/create", response_model=ServiceRequestResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def create_service_request(
    request: ServiceRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new service request.
    
    **Request Body:**
    - `service_type`: Type of service
    - `vehicle_id`: Vehicle ID (optional)
    - `vehicle_data`: Vehicle data (optional)
    - `customer_type`: Customer type
    - `customer_name`: Customer name
    - `customer_phone`: Customer phone
    - `customer_email`: Customer email
    - `company_name`: Company name
    - `purpose`: Service purpose
    - `notes`: Additional notes
    - `images`: Image URLs
    - `documents`: Document URLs
    - `metadata`: Additional metadata
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Created service request
    - `error`: Error message if unsuccessful
    """
    try:
        # Validate service type
        service = get_service_by_id(request.service_type)
        if not service:
            return ServiceRequestResponse(
                success=False,
                error=f"Invalid service type: {request.service_type}"
            )
        
        # Validate request data
        is_valid, error = validate_service_request_data(request.dict())
        if not is_valid:
            return ServiceRequestResponse(
                success=False,
                error=error
            )
        
        # Generate request number
        request_number = generate_request_number()
        
        # Prepare service request data
        request_data = {
            "request_number": request_number,
            "user_id": current_user.get("id"),
            "service_type": request.service_type,
            "vehicle_id": request.vehicle_id,
            "vehicle_data": request.vehicle_data,
            "customer_type": request.customer_type,
            "customer_name": request.customer_name or current_user.get("full_name"),
            "customer_phone": request.customer_phone or current_user.get("phone"),
            "customer_email": request.customer_email or current_user.get("email"),
            "company_name": request.company_name or current_user.get("company_name"),
            "purpose": request.purpose,
            "notes": request.notes,
            "images": request.images or [],
            "documents": request.documents or [],
            "metadata": request.metadata,
            "status": "pending",
            "payment_status": "pending",
            "service_price": service["price"],
            "created_at": format_timestamp(),
            "updated_at": format_timestamp()
        }
        
        # Save to Supabase
        result = supabase.table("service_requests").insert(request_data).execute()
        
        if not result.data:
            return ServiceRequestResponse(
                success=False,
                error="Failed to create service request"
            )
        
        return ServiceRequestResponse(
            success=True,
            data=result.data[0],
            message="Service request created successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Create service request error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


@router.get("/requests", response_model=ServiceRequestResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_service_requests(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status"),
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user service requests.
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50, max: 100)
    - `offset`: Number of results to skip (default: 0)
    - `status`: Filter by status
    - `service_type`: Filter by service type
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of service requests
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        # Build query
        query = supabase.table("service_requests") \
            .select("*") \
            .eq("user_id", current_user.get("id"))
        
        # Apply filters
        if status:
            query = query.eq("status", status)
        if service_type:
            query = query.eq("service_type", service_type)
        
        # Apply pagination
        query = query.order("created_at", desc=True) \
            .range(offset, offset + limit - 1)
        
        result = query.execute()
        
        return ServiceRequestResponse(
            success=True,
            data=result.data,
            count=len(result.data),
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get service requests error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


@router.get("/requests/{request_id}", response_model=ServiceRequestResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_service_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get service request by ID.
    
    **Path Parameter:**
    - `request_id`: Service request ID
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Service request details
    - `error`: Error message if unsuccessful
    """
    try:
        # Get service request
        result = supabase.table("service_requests") \
            .select("*") \
            .eq("id", request_id) \
            .execute()
        
        if not result.data:
            return ServiceRequestResponse(
                success=False,
                error="Service request not found"
            )
        
        request = result.data[0]
        
        # Check permissions
        if request.get("user_id") != current_user.get("id") and current_user.get("role") not in ["admin", "super_admin"]:
            return ServiceRequestResponse(
                success=False,
                error="Access denied"
            )
        
        return ServiceRequestResponse(
            success=True,
            data=request,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get service request error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


@router.put("/requests/{request_id}", response_model=ServiceRequestResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def update_service_request(
    request_id: str,
    update_data: ServiceRequestUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a service request.
    
    **Path Parameter:**
    - `request_id`: Service request ID
    
    **Request Body:**
    - `status`: New status
    - `payment_status`: New payment status
    - `notes`: Additional notes
    - `inspector`: Inspector data
    - `result`: Result data
    - `metadata`: Additional metadata
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Updated service request
    - `error`: Error message if unsuccessful
    """
    try:
        # Get service request
        result = supabase.table("service_requests") \
            .select("*") \
            .eq("id", request_id) \
            .execute()
        
        if not result.data:
            return ServiceRequestResponse(
                success=False,
                error="Service request not found"
            )
        
        request = result.data[0]
        
        # Check permissions
        if request.get("user_id") != current_user.get("id") and current_user.get("role") not in ["admin", "super_admin"]:
            return ServiceRequestResponse(
                success=False,
                error="Access denied"
            )
        
        # Prepare update data
        update_dict = update_data.dict(exclude_none=True)
        update_dict["updated_at"] = format_timestamp()
        
        # Update service request
        update_result = supabase.table("service_requests") \
            .update(update_dict) \
            .eq("id", request_id) \
            .execute()
        
        return ServiceRequestResponse(
            success=True,
            data=update_result.data[0] if update_result.data else None,
            message="Service request updated successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Update service request error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


@router.delete("/requests/{request_id}", response_model=ServiceRequestResponse)
@rate_limit(limit=5, per=60)
@require_auth
@log_request
@handle_errors
async def delete_service_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a service request.
    
    **Path Parameter:**
    - `request_id`: Service request ID
    
    **Response:**
    - `success`: Boolean indicating success
    - `message`: Status message
    - `error`: Error message if unsuccessful
    """
    try:
        # Get service request
        result = supabase.table("service_requests") \
            .select("*") \
            .eq("id", request_id) \
            .execute()
        
        if not result.data:
            return ServiceRequestResponse(
                success=False,
                error="Service request not found"
            )
        
        request = result.data[0]
        
        # Check permissions
        if request.get("user_id") != current_user.get("id") and current_user.get("role") not in ["admin", "super_admin"]:
            return ServiceRequestResponse(
                success=False,
                error="Access denied"
            )
        
        # Delete service request
        supabase.table("service_requests") \
            .delete() \
            .eq("id", request_id) \
            .execute()
        
        return ServiceRequestResponse(
            success=True,
            message="Service request deleted successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Delete service request error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


@router.get("/categories", response_model=ServiceRequestResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_service_categories(
    current_user: dict = Depends(get_current_user)
):
    """
    Get service categories.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of service categories
    """
    try:
        categories = [
            {"id": "valuation", "name": "Valuation", "description": "Vehicle valuation services"},
            {"id": "inspection", "name": "Inspection", "description": "Vehicle inspection services"},
            {"id": "assessment", "name": "Assessment", "description": "Vehicle assessment services"},
            {"id": "mileage", "name": "Mileage", "description": "Mileage rate calculations"},
            {"id": "fleet", "name": "Fleet", "description": "Fleet management services"},
            {"id": "certificate", "name": "Certificate", "description": "Certificate generation"},
            {"id": "report", "name": "Report", "description": "Custom report generation"},
            {"id": "instant", "name": "Instant", "description": "Instant services"}
        ]
        
        return ServiceRequestResponse(
            success=True,
            data=categories,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get service categories error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


@router.get("/stats", response_model=ServiceRequestResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_service_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get service statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Service statistics
    - `error`: Error message if unsuccessful
    """
    try:
        # Get all service requests for user
        result = supabase.table("service_requests") \
            .select("*") \
            .eq("user_id", current_user.get("id")) \
            .execute()
        
        requests = result.data
        
        total = len(requests)
        completed = len([r for r in requests if r.get("status") == "completed"])
        pending = len([r for r in requests if r.get("status") == "pending"])
        in_progress = len([r for r in requests if r.get("status") == "in_progress"])
        cancelled = len([r for r in requests if r.get("status") == "cancelled"])
        
        # Count by service type
        by_type = {}
        for r in requests:
            service_type = r.get("service_type", "unknown")
            by_type[service_type] = by_type.get(service_type, 0) + 1
        
        stats = {
            "total": total,
            "completed": completed,
            "pending": pending,
            "in_progress": in_progress,
            "cancelled": cancelled,
            "by_type": by_type
        }
        
        return ServiceRequestResponse(
            success=True,
            data=stats,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get service stats error: {str(e)}", exc_info=True)
        return ServiceRequestResponse(
            success=False,
            error=str(e)
        )


# ─── Export ────────────────────────────────────────────────────

__all__ = ['router']
