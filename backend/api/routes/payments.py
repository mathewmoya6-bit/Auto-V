"""
Payment Routes - FastAPI Version
Payment processing, M-Pesa integration, status checking, and history
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging

from app.core.database import supabase
from app.core.dependencies import get_current_user
from app.services.mpesa import mpesa_service
from app.utils.decorators import rate_limit, require_auth, require_role, log_request, handle_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


# ─── Pydantic Models ──────────────────────────────────────────

class PaymentInitiateRequest(BaseModel):
    """Payment initiation request model"""
    amount: float = Field(..., description="Payment amount", gt=0)
    service_type: str = Field(..., description="Service type")
    payment_method: str = Field(..., description="Payment method")
    service_id: Optional[str] = Field(None, description="Service ID")
    phone_number: Optional[str] = Field(None, description="Phone number for M-Pesa")
    description: Optional[str] = Field(None, description="Payment description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        valid_methods = ['mpesa', 'card', 'bank', 'cash']
        if v not in valid_methods:
            raise ValueError(f'Payment method must be one of: {", ".join(valid_methods)}')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v < 1:
            raise ValueError('Amount must be at least 1')
        if v > 10000000:
            raise ValueError('Amount cannot exceed 10,000,000')
        return v


class PaymentResponse(BaseModel):
    """Payment response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


class PaymentMethodResponse(BaseModel):
    """Payment method response model"""
    id: str
    name: str
    logo: Optional[str] = None
    is_active: bool


class PaymentStatsResponse(BaseModel):
    """Payment statistics response"""
    total_payments: int
    total_amount: float
    completed: int
    pending: int
    failed: int
    refunded: int
    currency: str = "KES"


# ─── Constants ──────────────────────────────────────────────────

PAYMENT_METHODS = [
    {
        "id": "mpesa",
        "name": "M-Pesa",
        "logo": "/images/mpesa.png",
        "is_active": True
    },
    {
        "id": "card",
        "name": "Card Payment",
        "logo": "/images/card.png",
        "is_active": False
    },
    {
        "id": "bank",
        "name": "Bank Transfer",
        "logo": "/images/bank.png",
        "is_active": False
    },
    {
        "id": "cash",
        "name": "Cash Payment",
        "logo": "/images/cash.png",
        "is_active": False
    }
]


# ─── Helper Functions ──────────────────────────────────────────

def generate_reference() -> str:
    """Generate a unique payment reference."""
    return f"PAY-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().isoformat()


def is_valid_service_type(service_type: str) -> bool:
    """Check if service type is valid."""
    valid_types = ['valuation', 'inspection', 'assessment', 'mileage', 'fleet', 'certificate', 'report']
    return service_type in valid_types


# ─── Routes ──────────────────────────────────────────────────

@router.get("/methods", response_model=PaymentResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_payment_methods(
    current_user: dict = Depends(get_current_user)
):
    """
    Get available payment methods.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of payment methods
    """
    return PaymentResponse(
        success=True,
        data=PAYMENT_METHODS,
        timestamp=format_timestamp()
    )


@router.post("/initiate", response_model=PaymentResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def initiate_payment(
    request: PaymentInitiateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate a payment.
    
    **Request Body:**
    - `amount`: Payment amount
    - `service_type`: Service type
    - `payment_method`: Payment method
    - `service_id`: Service ID (optional)
    - `phone_number`: Phone number for M-Pesa
    - `description`: Payment description
    - `metadata`: Additional metadata
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Payment details
    - `error`: Error message if unsuccessful
    """
    try:
        # Validate service type
        if not is_valid_service_type(request.service_type):
            return PaymentResponse(
                success=False,
                error=f"Invalid service type. Must be one of: valuation, inspection, assessment, mileage, fleet, certificate, report"
            )
        
        # Generate payment reference
        reference = generate_reference()
        
        # Prepare payment data
        payment_data = {
            "reference": reference,
            "amount": request.amount,
            "service_type": request.service_type,
            "payment_method": request.payment_method,
            "service_id": request.service_id,
            "user_id": current_user.get("id"),
            "status": "pending",
            "description": request.description,
            "metadata": request.metadata,
            "created_at": format_timestamp(),
            "updated_at": format_timestamp()
        }
        
        # Save to Supabase
        result = supabase.table("payments").insert(payment_data).execute()
        
        if not result.data:
            return PaymentResponse(
                success=False,
                error="Failed to initiate payment"
            )
        
        payment = result.data[0]
        
        # If M-Pesa, initiate STK Push
        if request.payment_method == "mpesa":
            if not request.phone_number:
                return PaymentResponse(
                    success=False,
                    error="Phone number is required for M-Pesa"
                )
            
            # Initiate STK Push
            mpesa_result = mpesa_service.stk_push(
                phone_number=request.phone_number,
                amount=request.amount,
                account_reference=reference,
                transaction_desc=f"AUTO-V {request.service_type}"
            )
            
            if not mpesa_result.get("success"):
                # Update payment status to failed
                supabase.table("payments") \
                    .update({
                        "status": "failed",
                        "error_message": mpesa_result.get("error", "M-Pesa initiation failed"),
                        "updated_at": format_timestamp()
                    }) \
                    .eq("reference", reference) \
                    .execute()
                
                return PaymentResponse(
                    success=False,
                    error=mpesa_result.get("error", "M-Pesa initiation failed")
                )
            
            # Update payment with checkout ID
            supabase.table("payments") \
                .update({
                    "checkout_request_id": mpesa_result.get("checkout_request_id"),
                    "merchant_request_id": mpesa_result.get("merchant_request_id"),
                    "phone_number": request.phone_number,
                    "updated_at": format_timestamp()
                }) \
                .eq("reference", reference) \
                .execute()
            
            return PaymentResponse(
                success=True,
                data={
                    "reference": reference,
                    "status": "pending",
                    "checkout_request_id": mpesa_result.get("checkout_request_id"),
                    "message": "M-Pesa STK Push initiated. Please check your phone."
                },
                timestamp=format_timestamp()
            )
        
        # For other payment methods
        return PaymentResponse(
            success=True,
            data={
                "reference": reference,
                "status": "pending",
                "message": "Payment initiated successfully"
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Initiate payment error: {str(e)}", exc_info=True)
        return PaymentResponse(
            success=False,
            error=str(e)
        )


@router.get("/{reference}", response_model=PaymentResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_payment_status(
    reference: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment status by reference.
    
    **Path Parameter:**
    - `reference`: Payment reference
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Payment details
    - `error`: Error message if unsuccessful
    """
    try:
        # Get payment from database
        result = supabase.table("payments") \
            .select("*") \
            .eq("reference", reference) \
            .execute()
        
        if not result.data:
            return PaymentResponse(
                success=False,
                error="Payment not found"
            )
        
        payment = result.data[0]
        
        # Check permissions
        if payment.get("user_id") != current_user.get("id") and current_user.get("role") not in ["admin", "super_admin"]:
            return PaymentResponse(
                success=False,
                error="Access denied"
            )
        
        return PaymentResponse(
            success=True,
            data=payment,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get payment status error: {str(e)}", exc_info=True)
        return PaymentResponse(
            success=False,
            error=str(e)
        )


@router.get("/history", response_model=PaymentResponse)
@rate_limit(limit=30, per=60)
@require_auth
@log_request
@handle_errors
async def get_payment_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user payment history.
    
    **Query Parameters:**
    - `limit`: Number of results to return (default: 50, max: 100)
    - `offset`: Number of results to skip (default: 0)
    - `status`: Filter by status
    - `service_type`: Filter by service type
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: List of payments
    - `count`: Total count
    - `error`: Error message if unsuccessful
    """
    try:
        # Build query
        query = supabase.table("payments") \
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
        
        return PaymentResponse(
            success=True,
            data={
                "payments": result.data,
                "count": len(result.data),
                "limit": limit,
                "offset": offset
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get payment history error: {str(e)}", exc_info=True)
        return PaymentResponse(
            success=False,
            error=str(e)
        )


@router.get("/stats", response_model=PaymentResponse)
@rate_limit(limit=20, per=60)
@require_auth
@log_request
@handle_errors
async def get_payment_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment statistics.
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Payment statistics
    - `error`: Error message if unsuccessful
    """
    try:
        # Get all payments for user
        result = supabase.table("payments") \
            .select("*") \
            .eq("user_id", current_user.get("id")) \
            .execute()
        
        payments = result.data
        
        total_payments = len(payments)
        total_amount = sum(p.get("amount", 0) for p in payments)
        
        completed = len([p for p in payments if p.get("status") == "completed"])
        pending = len([p for p in payments if p.get("status") == "pending"])
        failed = len([p for p in payments if p.get("status") == "failed"])
        refunded = len([p for p in payments if p.get("status") == "refunded"])
        
        stats = {
            "total_payments": total_payments,
            "total_amount": round(total_amount, 2),
            "completed": completed,
            "pending": pending,
            "failed": failed,
            "refunded": refunded,
            "currency": "KES"
        }
        
        return PaymentResponse(
            success=True,
            data=stats,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Get payment stats error: {str(e)}", exc_info=True)
        return PaymentResponse(
            success=False,
            error=str(e)
        )


@router.post("/callback/mpesa", response_model=PaymentResponse)
@log_request
@handle_errors
async def mpesa_callback(request: Request):
    """
    M-Pesa callback endpoint.
    
    **Request Body:** M-Pesa callback payload
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Callback processing result
    """
    try:
        # Get callback data
        callback_data = await request.json()
        logger.info(f"M-Pesa callback received: {callback_data}")
        
        # Process callback
        result = mpesa_service.process_callback(callback_data)
        
        if not result.get("success"):
            return PaymentResponse(
                success=False,
                error=result.get("error", "Callback processing failed")
            )
        
        return PaymentResponse(
            success=True,
            data=result,
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"M-Pesa callback error: {str(e)}", exc_info=True)
        return PaymentResponse(
            success=False,
            error=str(e)
        )


@router.post("/verify/{reference}", response_model=PaymentResponse)
@rate_limit(limit=10, per=60)
@require_auth
@log_request
@handle_errors
async def verify_payment(
    reference: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify a payment with M-Pesa.
    
    **Path Parameter:**
    - `reference`: Payment reference
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Verification result
    """
    try:
        # Get payment
        result = supabase.table("payments") \
            .select("*") \
            .eq("reference", reference) \
            .execute()
        
        if not result.data:
            return PaymentResponse(
                success=False,
                error="Payment not found"
            )
        
        payment = result.data[0]
        
        # Check permissions
        if payment.get("user_id") != current_user.get("id") and current_user.get("role") not in ["admin", "super_admin"]:
            return PaymentResponse(
                success=False,
                error="Access denied"
            )
        
        # If payment is already completed
        if payment.get("status") == "completed":
            return PaymentResponse(
                success=True,
                data={"status": "completed", "message": "Payment already completed"},
                timestamp=format_timestamp()
            )
        
        # If payment is not M-Pesa
        if payment.get("payment_method") != "mpesa":
            return PaymentResponse(
                success=False,
                error="Only M-Pesa payments can be verified"
            )
        
        # Get checkout request ID
        checkout_id = payment.get("checkout_request_id")
        if not checkout_id:
            return PaymentResponse(
                success=False,
                error="No checkout request ID found"
            )
        
        # Query M-Pesa status
        status_result = mpesa_service.query_status(checkout_id)
        
        if not status_result.get("success"):
            return PaymentResponse(
                success=False,
                error=status_result.get("error", "Failed to query payment status")
            )
        
        # Update payment status
        mpesa_status = status_result.get("status")
        if mpesa_status == "completed":
            supabase.table("payments") \
                .update({
                    "status": "completed",
                    "mpesa_receipt": status_result.get("receipt"),
                    "mpesa_result_code": status_result.get("result_code"),
                    "mpesa_result_desc": status_result.get("result_desc"),
                    "updated_at": format_timestamp(),
                    "completed_at": format_timestamp()
                }) \
                .eq("reference", reference) \
                .execute()
        elif mpesa_status == "failed":
            supabase.table("payments") \
                .update({
                    "status": "failed",
                    "mpesa_result_code": status_result.get("result_code"),
                    "mpesa_result_desc": status_result.get("result_desc"),
                    "updated_at": format_timestamp()
                }) \
                .eq("reference", reference) \
                .execute()
        
        return PaymentResponse(
            success=True,
            data={
                "status": mpesa_status,
                "receipt": status_result.get("receipt"),
                "result_code": status_result.get("result_code"),
                "result_desc": status_result.get("result_desc")
            },
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Verify payment error: {str(e)}", exc_info=True)
        return PaymentResponse(
            success=False,
            error=str(e)
        )


@router.post("/refund/{reference}", response_model=PaymentResponse)
@rate_limit(limit=5, per=60)
@require_role("admin")
@log_request
@handle_errors
async def refund_payment(
    reference: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Refund a payment (admin only).
    
    **Path Parameter:**
    - `reference`: Payment reference
    
    **Response:**
    - `success`: Boolean indicating success
    - `data`: Refund result
    - `error`: Error message if unsuccessful
    """
    try:
        # Get payment
        result = supabase.table("payments") \
            .select("*") \
            .eq("reference", reference) \
            .execute()
        
        if not result.data:
            return PaymentResponse(
                success=False,
                error="Payment not found"
            )
        
        payment = result.data[0]
        
        # Check if payment can be refunded
        if payment.get("status") != "completed":
            return PaymentResponse(
                success=False,
                error="Only completed payments can be refunded"
            )
        
        # Update payment status
        supabase.table("payments") \
            .update({
                "status": "refunded",
                "refunded_at": format_timestamp(),
                "refunded_by": current_user.get("id"),
                "updated_at": format_timestamp()
            }) \
            .eq("reference", reference) \
            .execute()
        
        return PaymentResponse(
            success=True,
            data={
                "reference": reference,
                "status": "refunded",
                "refunded_at": format_timestamp()
            },
            message="Payment refunded successfully",
            timestamp=format_timestamp()
        )
        
    except Exception as e:
        logger.error(f"Refund payment error: {str(e)}", exc_info=True)
        return PaymentResponse(
            success=False,
            error=str(e)
        )
