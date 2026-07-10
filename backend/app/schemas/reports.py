from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ReportBase(BaseModel):
    generated_at: datetime
    report_type: str
    user_id: str


class ValuationReport(BaseModel):
    vehicle_id: str
    vehicle_details: Dict[str, Any]
    current_valuation: float
    valuation_history: List[Dict[str, Any]]
    depreciation_rate: float
    recommended_price: float
    generated_at: datetime


class MileageReport(BaseModel):
    vehicle_id: str
    vehicle_details: Dict[str, Any]
    total_mileage: float
    average_daily_mileage: float
    mileage_entries: List[Dict[str, Any]]
    usage_trend: str
    generated_at: datetime


class InspectionReportSummary(BaseModel):
    vehicle_id: str
    vehicle_details: Dict[str, Any]
    total_inspections: int
    last_inspection_date: Optional[datetime]
    overall_condition: str
    issues_found: List[str]
    recommendations: List[str]
    generated_at: datetime


class ComprehensiveVehicleReport(BaseModel):
    vehicle: Dict[str, Any]
    valuation: Optional[Dict[str, Any]]
    mileage_history: List[Dict[str, Any]]
    inspections: List[Dict[str, Any]]
    summary: Dict[str, Any]
    generated_at: datetime


class ReportRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    vehicle_id: Optional[str] = None
    report_format: str = "json"  # json, pdf, csv


class ReportResponse(BaseModel):
    report_id: str
    report_type: str
    generated_at: datetime
    data: Dict[str, Any]
    download_url: Optional[str] = None
