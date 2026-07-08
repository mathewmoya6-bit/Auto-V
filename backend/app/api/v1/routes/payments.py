# app/api/v1/routes/payments.py
# =============================================================================
# AUTO-V API - Payment Routes
# =============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from app.schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    MpesaPaymentRequest,
    MpesaPaymentResponse,
)
from app.services.mpesa import MpesaService

# TODO: replace with the real import path for your auth dependency once confirmed.
# Likely candidates based on your project structure:
#   from app.api.v1.routes.auth import get_current_user
#   from app.services.auth_service import get_current_user
# from <real_module> import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])

mpesa_service = MpesaService()


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment: PaymentCreate,
    current_user=Depends(get_current_user),
):
    # TODO: persist payment record via PaymentService
    raise NotImplementedError


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    current_user=Depends(get_current_user),
):
    # TODO: fetch payment by id via PaymentService
    raise NotImplementedError


@router.patch("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: UUID,
    payment_update: PaymentUpdate,
    current_user=Depends(get_current_user),
):
    # TODO: update payment via PaymentService
    raise NotImplementedError


@router.post("/mpesa/stk-push", response_model=MpesaPaymentResponse)
async def initiate_mpesa_payment(
    request: MpesaPaymentRequest,
    current_user=Depends(get_current_user),
):
    result = await mpesa_service.stk_push(
        amount=request.amount,
        phone_number=request.phone_number,
        account_reference=request.account_reference,
        transaction_desc=request.transaction_desc,
    )
    return MpesaPaymentResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        checkout_request_id=result.get("CheckoutRequestID"),
        merchant_request_id=result.get("MerchantRequestID"),
    )
