from fastapi import APIRouter, HTTPException, Depends
from app.services.payment_service import PaymentService
from app.schemas.payments import PaymentRequest, PaymentResponse, PaymentStatus
from app.core.security import get_current_active_user

router = APIRouter()
payment_service = PaymentService()


@router.post("/payments/initiate", response_model=PaymentResponse)
async def initiate_payment(
    payment: PaymentRequest,
    current_user = Depends(get_current_active_user)
):
    """Initiate M-Pesa payment"""
    try:
        response = await payment_service.initiate_payment(
            user_id=current_user.id,
            amount=payment.amount,
            phone_number=payment.phone_number,
            description=payment.description
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/status/{payment_id}", response_model=PaymentStatus)
async def get_payment_status(
    payment_id: str,
    current_user = Depends(get_current_active_user)
):
    """Check payment status"""
    try:
        status = await payment_service.get_payment_status(payment_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/history")
async def get_payment_history(
    current_user = Depends(get_current_active_user),
    limit: int = 50
):
    """Get user's payment history"""
    try:
        history = await payment_service.get_payment_history(
            user_id=current_user.id,
            limit=limit
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
