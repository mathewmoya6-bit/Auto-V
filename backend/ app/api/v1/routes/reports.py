# app/api/v1/routes/reports.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import json
import base64

from app.core.config import settings
from app.core.database import get_db
from app.core.security import JWTBearer
from app.core.logging import get_logger

router = APIRouter(prefix="/reports", tags=["Reports"])
logger = get_logger(__name__)

class ReportResponse(BaseModel):
    id: str
    user_id: str
    vehicle_id: str
    payment_id: Optional[str] = None
    valuation_id: Optional[str] = None
    report_type: str
    title: str
    content: Dict[str, Any]
    status: str
    created_at: str
    updated_at: str

@router.post("/generate/{vehicle_id}")
async def generate_report(
    vehicle_id: str,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """Generate a valuation report for a vehicle"""
    try:
        user_id = request.state.user_id
        
        # Check vehicle exists and belongs to user
        vehicle_result = db.table('vehicles').select('*').eq('id', vehicle_id).execute()
        if not vehicle_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        vehicle = vehicle_result.data[0]
        if vehicle['user_id'] != user_id and request.state.user_role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get latest valuation
        valuation_result = db.table('valuations') \
            .select('*') \
            .eq('vehicle_id', vehicle_id) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
        
        valuation = valuation_result.data[0] if valuation_result.data else None
        
        if not valuation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No valuation found for this vehicle"
            )
        
        # Generate report content
        report_content = {
            'vehicle_details': {
                'make': vehicle.get('make'),
                'model': vehicle.get('model'),
                'year': vehicle.get('year'),
                'vin': vehicle.get('vin'),
                'color': vehicle.get('color'),
                'mileage': vehicle.get('mileage'),
                'engine_type': vehicle.get('engine_type'),
                'transmission': vehicle.get('transmission'),
                'fuel_type': vehicle.get('fuel_type'),
                'condition': vehicle.get('condition'),
                'description': vehicle.get('description')
            },
            'valuation_summary': {
                'estimated_value': valuation.get('estimated_value'),
                'min_value': valuation.get('min_value'),
                'max_value': valuation.get('max_value'),
                'confidence_score': valuation.get('confidence_score'),
                'valuation_type': valuation.get('valuation_type'),
                'ai_confidence': valuation.get('ai_confidence'),
                'created_at': valuation.get('created_at'),
                'expires_at': valuation.get('expires_at')
            },
            'market_comparison': valuation.get('market_comparison'),
            'depreciation_data': valuation.get('depreciation_data'),
            'generated_at': datetime.utcnow().isoformat(),
            'report_id': str(uuid.uuid4())
        }
        
        # Create report record
        report_id = str(uuid.uuid4())
        report_data = {
            'id': report_id,
            'user_id': user_id,
            'vehicle_id': vehicle_id,
            'valuation_id': valuation['id'],
            'report_type': 'valuation',
            'title': f"Valuation Report - {vehicle.get('make')} {vehicle.get('model')} ({vehicle.get('year')})",
            'content': report_content,
            'status': 'generated',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        db.table('reports').insert(report_data).execute()
        
        # If report generation feature is enabled
        if settings.FEATURE_REPORT_GENERATION:
            # Generate PDF report (placeholder)
            # await generate_pdf_report(report_data)
            pass
        
        logger.info(f"Report generated: {report_id} for vehicle {vehicle_id}")
        
        return ReportResponse(**report_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate report error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """Get report by ID"""
    try:
        user_id = request.state.user_id
        
        result = db.table('reports').select('*').eq('id', report_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        report = result.data[0]
        
        # Check access
        if report['user_id'] != user_id and request.state.user_role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return ReportResponse(**report)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get report error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get report"
        )

@router.get("/vehicle/{vehicle_id}")
async def get_vehicle_reports(
    vehicle_id: str,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db),
    limit: int = 10,
    offset: int = 0
):
    """Get all reports for a vehicle"""
    try:
        user_id = request.state.user_id
        
        # Check vehicle ownership
        vehicle_result = db.table('vehicles').select('*').eq('id', vehicle_id).execute()
        if not vehicle_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        vehicle = vehicle_result.data[0]
        if vehicle['user_id'] != user_id and request.state.user_role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        result = db.table('reports') \
            .select('*') \
            .eq('vehicle_id', vehicle_id) \
            .order('created_at', desc=True) \
            .range(offset, offset + limit) \
            .execute()
        
        return {
            'reports': result.data,
            'total': len(result.data),
            'limit': limit,
            'offset': offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get vehicle reports error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get reports"
        )

@router.get("/me/reports")
async def get_my_reports(
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """Get current user's reports"""
    try:
        user_id = request.state.user_id
        
        result = db.table('reports') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .range(offset, offset + limit) \
            .execute()
        
        return {
            'reports': result.data,
            'total': len(result.data),
            'limit': limit,
            'offset': offset
        }
        
    except Exception as e:
        logger.error(f"Get my reports error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get reports"
        )

@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """Delete a report"""
    try:
        user_id = request.state.user_id
        
        # Check report exists
        result = db.table('reports').select('*').eq('id', report_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        report = result.data[0]
        
        # Check ownership
        if report['user_id'] != user_id and request.state.user_role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        db.table('reports').delete().eq('id', report_id).execute()
        
        logger.info(f"Report deleted: {report_id}")
        
        return {"message": "Report deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete report error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete report"
        )
