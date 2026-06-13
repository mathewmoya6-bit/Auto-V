from fastapi import FastAPI, UploadFile, File
import shutil
import os

from services.valuation_service import ValuationService
from services.inspection_service import InspectionService
from services.ocr_service import OCRPipelineService
from services.fraud_service import FraudService
from services.maintenance_service import MaintenanceService

app = FastAPI(title="AUTO-V AI Engine")

valuation_service = ValuationService()
inspection_service = InspectionService()
ocr_service = OCRPipelineService()
fraud_service = FraudService()
maintenance_service = MaintenanceService()
