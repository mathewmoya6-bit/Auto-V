from fastapi import APIRouter, Request, HTTPException
from services.mpesa import mpesa_service
from services.logger import logger
from config import settings

router = APIRouter()

@router.post("/mpesa-callback")
async def mpesa_callback(request: Request):
    try:
        data = await request.json()
        logger.info(f"M-Pesa callback received: {data}")
        
        # Process the callback
        result_code = data.get("Body", {}).get("stkCallback", {}).get("ResultCode")
        checkout_request_id = data.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")
        
        if result_code == 0:
            # Payment successful
            await mpesa_service.handle_successful_payment(checkout_request_id, data)
        else:
            # Payment failed
            await mpesa_service.handle_failed_payment(checkout_request_id, data)
        
        return {"message": "Callback processed successfully"}
    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
