from fastapi import FastAPI, Depends, HTTPException
from typing import Dict, Any
from services.admin_service import AdminService
from middleware import require_role

app = FastAPI()

# Initialize service
admin_service = AdminService()

# Type hint for the dependency result
from fastapi.security import HTTPAuthorizationHeader

# 🏠 ADMIN DASHBOARD
@app.get("/admin/dashboard")
async def admin_dashboard(
    auth: dict = Depends(require_role(["admin"]))
) -> Dict[str, Any]:
    """
    Admin dashboard - only accessible by admin users
    """
    try:
        return {
            "status": "success",
            "user_id": auth["user_id"],
            "data": {
                "vehicles": admin_service.get_all_vehicles(),
                "inspections": admin_service.get_all_inspections(),
                "valuations": admin_service.get_all_valuations(),
                "payments": admin_service.get_all_payments()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🏦 BANK VIEW (LOW RISK VEHICLES)
@app.get("/bank/vehicles")
async def bank_view(
    auth: dict = Depends(require_role(["bank", "admin"]))
) -> Dict[str, Any]:
    """
    Bank view - accessible by bank and admin users
    """
    try:
        # You need to inject supabase client (better to use dependency)
        from services.supabase_client import get_supabase
        supabase = get_supabase()
        
        data = supabase.table("vehicles") \
            .select("*, valuations(*)") \
            .execute()
        
        return {
            "status": "success",
            "user_id": auth["user_id"],
            "role": auth["role"],
            "data": data.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🛡️ INSURANCE VIEW (RISK ANALYSIS)
@app.get("/insurance/risk")
async def insurance_view(
    auth: dict = Depends(require_role(["insurer", "admin"]))
) -> Dict[str, Any]:
    """
    Insurance view - accessible by insurer and admin users
    """
    try:
        from services.supabase_client import get_supabase
        supabase = get_supabase()
        
        data = supabase.table("valuations") \
            .select("*, vehicles(*)") \
            .execute()
        
        # Add risk analysis
        risk_analysis = analyze_risk(data.data)  # Implement this
        
        return {
            "status": "success",
            "user_id": auth["user_id"],
            "role": auth["role"],
            "data": data.data,
            "risk_analysis": risk_analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
