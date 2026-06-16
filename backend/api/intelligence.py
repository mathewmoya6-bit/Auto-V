# ============================================
# AUTO-V INTELLIGENCE API ENDPOINTS
# ============================================

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from typing import Optional
import asyncpg
from datetime import datetime, timedelta

app = FastAPI(title="AUTO-V Intelligence API", version="2.0.0")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ============================================
# VEHICLE INTELLIGENCE ENDPOINTS
# ============================================

@app.get("/api/intelligence/vehicle/{registration}")
async def get_vehicle_intelligence(registration: str, api_key: str = Depends(api_key_header)):
    """
    Get complete vehicle intelligence report
    Returns: Vehicle Identity, Market Value, Inspection Status, History, Risk Score
    """
    # Check API key
    if api_key:
        await log_api_usage(api_key, "/api/intelligence/vehicle")
    
    # Get vehicle intelligence data
    vehicle = await get_vehicle_by_registration(registration)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    
    intelligence = await get_intelligence_data(vehicle['id'])
    
    return {
        "vehicle": {
            "registration": vehicle['registration_number'],
            "make": vehicle['make'],
            "model": vehicle['model'],
            "year": vehicle['year'],
            "color": vehicle['color'],
            "mileage": vehicle['current_mileage']
        },
        "valuation": {
            "market_value": intelligence['market_value'],
            "insurance_value": intelligence['insurance_value'],
            "trade_in_value": intelligence['trade_in_value']
        },
        "inspection": {
            "score": intelligence['condition_score'],
            "rating": intelligence['risk_level'],
            "last_inspection": intelligence['last_inspection_date']
        },
        "risk": {
            "score": intelligence['risk_score'],
            "level": intelligence['risk_level'],
            "indicators": intelligence['risk_indicators']
        },
        "history": {
            "valuation_count": intelligence['valuation_count'],
            "inspection_count": intelligence['inspection_count'],
            "average_value": intelligence['average_valuation']
        },
        "market_trend": intelligence['market_trend']
    }

@app.get("/api/intelligence/vehicle/{registration}/history")
async def get_vehicle_history(registration: str):
    """Get complete vehicle history report"""
    vehicle = await get_vehicle_by_registration(registration)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    
    history = await get_vehicle_history_data(vehicle['id'])
    return {
        "registration": registration,
        "valuations": history['valuations'],
        "inspections": history['inspections'],
        "mileage_history": history['mileage_history'],
        "ownership_history": history['ownership_history'],
        "market_trends": history['market_trends']
    }

@app.get("/api/intelligence/vehicle/{registration}/risk")
async def get_risk_assessment(registration: str):
    """Get insurance risk assessment"""
    vehicle = await get_vehicle_by_registration(registration)
    if not vehicle:
        raise HTTPException(404, "Vehicle not found")
    
    risk = await calculate_risk_score(vehicle['id'])
    return {
        "registration": registration,
        "risk_score": risk['score'],
        "risk_level": risk['level'],
        "accident_risk": risk['accident_risk'],
        "theft_risk": risk['theft_risk'],
        "fraud_indicators": risk['fraud_indicators'],
        "recommendation": risk['recommendation']
    }

# ============================================
# FLEET INTELLIGENCE ENDPOINTS
# ============================================

@app.get("/api/fleet/{organization_id}/dashboard")
async def get_fleet_dashboard(organization_id: str):
    """Get complete fleet intelligence dashboard"""
    fleet = await get_fleet_data(organization_id)
    return {
        "total_vehicles": fleet['total'],
        "total_value": fleet['total_value'],
        "average_age": fleet['average_age'],
        "inspection_due": fleet['inspection_due'],
        "depreciation_rate": fleet['depreciation_rate'],
        "maintenance_alerts": fleet['alerts'],
        "vehicles": fleet['vehicles']
    }

# ============================================
# DEALER INTELLIGENCE ENDPOINTS
# ============================================

@app.get("/api/dealer/{dealer_id}/inventory")
async def get_dealer_inventory(dealer_id: str):
    """Get dealer inventory intelligence"""
    inventory = await get_dealer_inventory_data(dealer_id)
    return {
        "total_vehicles": inventory['total'],
        "total_value": inventory['total_value'],
        "average_days_on_lot": inventory['average_days'],
        "stock_aging": inventory['stock_aging'],
        "demand_analysis": inventory['demand_analysis'],
        "vehicles": inventory['vehicles']
    }

# ============================================
# MARKET INTELLIGENCE ENDPOINTS
# ============================================

@app.get("/api/market/trends")
async def get_market_trends(make: Optional[str] = None, model: Optional[str] = None):
    """Get market trends and predictive pricing"""
    trends = await get_market_trend_data(make, model)
    return {
        "trends": trends['trends'],
        "predictions": trends['predictions'],
        "average_values": trends['averages'],
        "confidence_score": trends['confidence']
    }

# ============================================
# AI ENDPOINTS
# ============================================

@app.post("/api/ai/damage-detection")
async def detect_damage(request: Request):
    """AI-powered damage detection from images"""
    data = await request.json()
    images = data.get('images', [])
    
    results = []
    for image in images:
        detection = await process_damage_detection(image)
        results.append(detection)
    
    return {
        "detections": results,
        "overall_score": calculate_overall_score(results),
        "estimated_repair_cost": sum(r['repair_cost'] for r in results)
    }

@app.post("/api/ai/valuation")
async def ai_valuation(request: Request):
    """AI-powered valuation assistant"""
    data = await request.json()
    
    valuation = await calculate_ai_valuation(
        make=data['make'],
        model=data['model'],
        year=data['year'],
        mileage=data['mileage']
    )
    
    return {
        "market_value": valuation['market_value'],
        "insurance_value": valuation['insurance_value'],
        "confidence_score": valuation['confidence'],
        "factors": valuation['factors']
    }

# ============================================
# VERIFICATION NETWORK ENDPOINTS
# ============================================

@app.get("/api/verify/{certificate_number}")
async def verify_certificate(certificate_number: str, request: Request):
    """Public certificate verification"""
    cert = await get_certificate(certificate_number)
    if not cert:
        return {"valid": False, "message": "Certificate not found"}
    
    is_valid = cert['valid_until'] > datetime.now()
    
    # Log verification
    await log_verification(certificate_number, request.client.host)
    
    return {
        "valid": is_valid,
        "certificate_number": certificate_number,
        "vehicle": cert['vehicle'],
        "valuation": cert['valuation'],
        "issue_date": cert['issue_date'],
        "valid_until": cert['valid_until'],
        "status": "Valid" if is_valid else "Expired"
    }

# ============================================
# MARKETPLACE ENDPOINTS
# ============================================

@app.get("/api/marketplace/vehicles")
async def get_marketplace_vehicles(
    make: Optional[str] = None,
    model: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None
):
    """Get verified marketplace vehicles"""
    vehicles = await get_marketplace_listings(make, model, min_price, max_price)
    return {
        "total": len(vehicles),
        "vehicles": vehicles
    }

@app.post("/api/marketplace/vehicle/{vehicle_id}/finance")
async def request_financing(vehicle_id: str, request: Request):
    """Request financing for a vehicle"""
    data = await request.json()
    
    financing = await process_financing_request(
        vehicle_id=vehicle_id,
        amount=data['amount'],
        tenure=data['tenure'],
        institution=data['institution']
    )
    
    return {
        "status": "pending",
        "reference": financing['reference'],
        "estimated_terms": financing['terms']
    }
