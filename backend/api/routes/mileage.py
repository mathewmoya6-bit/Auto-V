"""
Mileage Service - FastAPI Version
Vehicle mileage rate calculations, cost analysis, and fuel economy
Based on Kenya Vehicle Running Costs Report 2024
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date
from decimal import Decimal
import json

from app.core.database import supabase

logger = logging.getLogger(__name__)


# ─── Constants ──────────────────────────────────────────────────

# Vehicle categories from Kenya Running Costs Report
VEHICLE_CATEGORIES = {
    # Saloon - Petrol
    "PS-850": {
        "name": "Petrol Saloon Up to 850cc",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 0,
        "engine_cc_max": 850,
        "drive_type": "2WD",
        "average_initial_cost": 985500,
        "fixed_cost_per_km": 14.79,
        "operating_cost_per_km": 14.37,
        "total_cost_per_km": 29.16,
        "fuel_cost_km": 11.51,
        "servicing_cost_km": 0.87,
        "repairs_cost_km": 1.31,
        "tyres_cost_km": 0.66,
        "annual_fixed_cost": 443793,
        "annual_km": 30000
    },
    "PS-1050": {
        "name": "Petrol Saloon 851-1050cc",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 851,
        "engine_cc_max": 1050,
        "drive_type": "2WD",
        "average_initial_cost": 1200000,
        "fixed_cost_per_km": 17.29,
        "operating_cost_per_km": 16.44,
        "total_cost_per_km": 33.73,
        "fuel_cost_km": 12.96,
        "servicing_cost_km": 1.06,
        "repairs_cost_km": 1.60,
        "tyres_cost_km": 0.80,
        "annual_fixed_cost": 518600,
        "annual_km": 30000
    },
    "PS-1250": {
        "name": "Petrol Saloon 1051-1250cc",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 1051,
        "engine_cc_max": 1250,
        "drive_type": "2WD",
        "average_initial_cost": 1620000,
        "fixed_cost_per_km": 22.17,
        "operating_cost_per_km": 18.52,
        "total_cost_per_km": 40.68,
        "fuel_cost_km": 13.82,
        "servicing_cost_km": 1.44,
        "repairs_cost_km": 2.16,
        "tyres_cost_km": 1.08,
        "annual_fixed_cost": 665075,
        "annual_km": 30000
    },
    "PS-1350": {
        "name": "Petrol Saloon 1251-1350cc",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 1251,
        "engine_cc_max": 1350,
        "drive_type": "2WD",
        "average_initial_cost": 2800000,
        "fixed_cost_per_km": 35.89,
        "operating_cost_per_km": 22.40,
        "total_cost_per_km": 58.28,
        "fuel_cost_km": 14.30,
        "servicing_cost_km": 2.48,
        "repairs_cost_km": 3.73,
        "tyres_cost_km": 1.87,
        "annual_fixed_cost": 1076600,
        "annual_km": 30000
    },
    "PS-1500": {
        "name": "Petrol Saloon 1300-1500cc",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 1300,
        "engine_cc_max": 1500,
        "drive_type": "2WD",
        "average_initial_cost": 2700000,
        "fixed_cost_per_km": 34.72,
        "operating_cost_per_km": 23.07,
        "total_cost_per_km": 57.80,
        "fuel_cost_km": 15.26,
        "servicing_cost_km": 2.39,
        "repairs_cost_km": 3.60,
        "tyres_cost_km": 1.80,
        "annual_fixed_cost": 1041725,
        "annual_km": 30000
    },
    "PS-1650": {
        "name": "Petrol Saloon 1451-1650cc",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 1451,
        "engine_cc_max": 1650,
        "drive_type": "2WD",
        "average_initial_cost": 3300000,
        "fixed_cost_per_km": 41.70,
        "operating_cost_per_km": 25.48,
        "total_cost_per_km": 67.18,
        "fuel_cost_km": 15.93,
        "servicing_cost_km": 2.93,
        "repairs_cost_km": 4.40,
        "tyres_cost_km": 2.20,
        "annual_fixed_cost": 1250975,
        "annual_km": 30000
    },
    "PS-1850A": {
        "name": "Petrol Saloon 1651-1850cc (A)",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 1651,
        "engine_cc_max": 1850,
        "drive_type": "2WD",
        "load_rating": "A",
        "average_initial_cost": 3750000,
        "fixed_cost_per_km": 46.93,
        "operating_cost_per_km": 28.12,
        "total_cost_per_km": 75.05,
        "fuel_cost_km": 17.28,
        "servicing_cost_km": 3.33,
        "repairs_cost_km": 5.00,
        "tyres_cost_km": 2.50,
        "annual_fixed_cost": 1407913,
        "annual_km": 30000
    },
    "PS-1850B": {
        "name": "Petrol Saloon 1651-1850cc (B)",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 1651,
        "engine_cc_max": 1850,
        "drive_type": "2WD",
        "load_rating": "B",
        "average_initial_cost": 6500000,
        "fixed_cost_per_km": 78.90,
        "operating_cost_per_km": 36.06,
        "total_cost_per_km": 114.96,
        "fuel_cost_km": 17.28,
        "servicing_cost_km": 5.76,
        "repairs_cost_km": 8.67,
        "tyres_cost_km": 4.33,
        "annual_fixed_cost": 2366975,
        "annual_km": 30000
    },
    "PS-2000A": {
        "name": "Petrol Saloon 1851-2000cc (A)",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 1851,
        "engine_cc_max": 2000,
        "drive_type": "2WD",
        "load_rating": "A",
        "average_initial_cost": 4100000,
        "fixed_cost_per_km": 51.00,
        "operating_cost_per_km": 30.68,
        "total_cost_per_km": 81.68,
        "fuel_cost_km": 18.83,
        "servicing_cost_km": 3.64,
        "repairs_cost_km": 5.47,
        "tyres_cost_km": 2.73,
        "annual_fixed_cost": 1529975,
        "annual_km": 30000
    },
    "PS-2000B": {
        "name": "Petrol Saloon 1851-2000cc (B)",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 1851,
        "engine_cc_max": 2000,
        "drive_type": "2WD",
        "load_rating": "B",
        "average_initial_cost": 7000000,
        "fixed_cost_per_km": 84.71,
        "operating_cost_per_km": 39.05,
        "total_cost_per_km": 123.77,
        "fuel_cost_km": 18.83,
        "servicing_cost_km": 6.21,
        "repairs_cost_km": 9.33,
        "tyres_cost_km": 4.67,
        "annual_fixed_cost": 2541350,
        "annual_km": 30000
    },
    "PS-2300A": {
        "name": "Petrol Saloon 2001-2300cc (A)",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 2001,
        "engine_cc_max": 2300,
        "drive_type": "2WD",
        "load_rating": "A",
        "average_initial_cost": 3950000,
        "fixed_cost_per_km": 45.18,
        "operating_cost_per_km": 31.14,
        "total_cost_per_km": 76.33,
        "fuel_cost_km": 20.74,
        "servicing_cost_km": 3.19,
        "repairs_cost_km": 4.80,
        "tyres_cost_km": 2.40,
        "annual_fixed_cost": 1355500,
        "annual_km": 30000
    },
    "PS-2300B": {
        "name": "Petrol Saloon 2001-2300cc (B)",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 2001,
        "engine_cc_max": 2300,
        "drive_type": "2WD",
        "load_rating": "B",
        "average_initial_cost": 5500000,
        "fixed_cost_per_km": 89.48,
        "operating_cost_per_km": 39.51,
        "total_cost_per_km": 128.99,
        "fuel_cost_km": 20.74,
        "servicing_cost_km": 5.76,
        "repairs_cost_km": 8.67,
        "tyres_cost_km": 4.33,
        "annual_fixed_cost": 2684375,
        "annual_km": 30000
    },
    "PS-2600": {
        "name": "Petrol Saloon 2301-2600cc",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 2301,
        "engine_cc_max": 2600,
        "drive_type": "2WD",
        "average_initial_cost": 7700000,
        "fixed_cost_per_km": 92.61,
        "operating_cost_per_km": 48.16,
        "total_cost_per_km": 140.77,
        "fuel_cost_km": 25.93,
        "servicing_cost_km": 6.83,
        "repairs_cost_km": 10.27,
        "tyres_cost_km": 5.13,
        "annual_fixed_cost": 2778445,
        "annual_km": 30000
    },
    "PS-2601": {
        "name": "Petrol Saloon Over 2601cc",
        "type": "Saloon",
        "engine_type": "Petrol",
        "engine_cc_min": 2601,
        "engine_cc_max": 9999,
        "drive_type": "2WD",
        "average_initial_cost": 11000000,
        "fixed_cost_per_km": 131.21,
        "operating_cost_per_km": 57.70,
        "total_cost_per_km": 188.91,
        "fuel_cost_km": 25.93,
        "servicing_cost_km": 9.75,
        "repairs_cost_km": 14.67,
        "tyres_cost_km": 7.33,
        "annual_fixed_cost": 3936250,
        "annual_km": 30000
    },
    # Diesel Saloon
    "DS-1450": {
        "name": "Diesel Saloon 1351-1450cc",
        "type": "Saloon",
        "engine_type": "Diesel",
        "engine_cc_min": 1351,
        "engine_cc_max": 1450,
        "drive_type": "2WD",
        "average_initial_cost": 3000000,
        "fixed_cost_per_km": 38.21,
        "operating_cost_per_km": 24.03,
        "total_cost_per_km": 62.24,
        "fuel_cost_km": 15.36,
        "servicing_cost_km": 2.66,
        "repairs_cost_km": 4.00,
        "tyres_cost_km": 2.00,
        "annual_fixed_cost": 1146350,
        "annual_km": 30000
    },
    "DS-2000": {
        "name": "Diesel Saloon 1501-2000cc",
        "type": "Saloon",
        "engine_type": "Diesel",
        "engine_cc_min": 1501,
        "engine_cc_max": 2000,
        "drive_type": "2WD",
        "average_initial_cost": 4200000,
        "fixed_cost_per_km": 52.16,
        "operating_cost_per_km": 27.91,
        "total_cost_per_km": 80.07,
        "fuel_cost_km": 15.77,
        "servicing_cost_km": 3.72,
        "repairs_cost_km": 5.60,
        "tyres_cost_km": 2.80,
        "annual_fixed_cost": 1564850,
        "annual_km": 30000
    },
    # 4WD Estate Petrol
    "4WD-P-1600": {
        "name": "4WD Estate Petrol 1001-1600cc",
        "type": "Estate",
        "engine_type": "Petrol",
        "engine_cc_min": 1001,
        "engine_cc_max": 1600,
        "drive_type": "4WD",
        "average_initial_cost": 2500000,
        "fixed_cost_per_km": 32.40,
        "operating_cost_per_km": 25.26,
        "total_cost_per_km": 57.65,
        "fuel_cost_km": 18.03,
        "servicing_cost_km": 2.22,
        "repairs_cost_km": 3.33,
        "tyres_cost_km": 1.67,
        "annual_fixed_cost": 971875,
        "annual_km": 30000
    },
    "4WD-P-2000": {
        "name": "4WD Estate Petrol 1601-2000cc",
        "type": "Estate",
        "engine_type": "Petrol",
        "engine_cc_min": 1601,
        "engine_cc_max": 2000,
        "drive_type": "4WD",
        "average_initial_cost": 5000000,
        "fixed_cost_per_km": 61.46,
        "operating_cost_per_km": 37.48,
        "total_cost_per_km": 98.94,
        "fuel_cost_km": 23.03,
        "servicing_cost_km": 4.43,
        "repairs_cost_km": 6.67,
        "tyres_cost_km": 3.33,
        "annual_fixed_cost": 1843750,
        "annual_km": 30000
    },
    "4WD-P-3000A": {
        "name": "4WD Estate Petrol 2001-3000cc (A)",
        "type": "Estate",
        "engine_type": "Petrol",
        "engine_cc_min": 2001,
        "engine_cc_max": 3000,
        "drive_type": "4WD",
        "load_rating": "A",
        "average_initial_cost": 6000000,
        "fixed_cost_per_km": 73.08,
        "operating_cost_per_km": 43.27,
        "total_cost_per_km": 116.35,
        "fuel_cost_km": 25.93,
        "servicing_cost_km": 5.32,
        "repairs_cost_km": 8.00,
        "tyres_cost_km": 4.00,
        "annual_fixed_cost": 2192500,
        "annual_km": 30000
    },
    "4WD-P-3000B": {
        "name": "4WD Estate Petrol 2001-3000cc (B)",
        "type": "Estate",
        "engine_type": "Petrol",
        "engine_cc_min": 2001,
        "engine_cc_max": 3000,
        "drive_type": "4WD",
        "load_rating": "B",
        "average_initial_cost": 9900000,
        "fixed_cost_per_km": 118.42,
        "operating_cost_per_km": 54.52,
        "total_cost_per_km": 172.94,
        "fuel_cost_km": 25.93,
        "servicing_cost_km": 8.78,
        "repairs_cost_km": 13.20,
        "tyres_cost_km": 6.60,
        "annual_fixed_cost": 3552625,
        "annual_km": 30000
    },
    "4WD-P-4800A": {
        "name": "4WD Estate Petrol 3001-4800cc (A)",
        "type": "Estate",
        "engine_type": "Petrol",
        "engine_cc_min": 3001,
        "engine_cc_max": 4800,
        "drive_type": "4WD",
        "load_rating": "A",
        "average_initial_cost": 9200000,
        "fixed_cost_per_km": 134.82,
        "operating_cost_per_km": 58.48,
        "total_cost_per_km": 193.30,
        "fuel_cost_km": 31.91,
        "servicing_cost_km": 8.16,
        "repairs_cost_km": 12.27,
        "tyres_cost_km": 6.13,
        "annual_fixed_cost": 4044500,
        "annual_km": 30000
    },
    "4WD-P-4800B": {
        "name": "4WD Estate Petrol 3001-4800cc (B)",
        "type": "Estate",
        "engine_type": "Petrol",
        "engine_cc_min": 3001,
        "engine_cc_max": 4800,
        "drive_type": "4WD",
        "load_rating": "B",
        "average_initial_cost": 18000000,
        "fixed_cost_per_km": 260.58,
        "operating_cost_per_km": 83.89,
        "total_cost_per_km": 344.47,
        "fuel_cost_km": 31.91,
        "servicing_cost_km": 15.96,
        "repairs_cost_km": 24.24,
        "tyres_cost_km": 12.00,
        "annual_fixed_cost": 7817500,
        "annual_km": 30000
    },
    # 4WD Estate Diesel
    "4WD-D-1999": {
        "name": "4WD Estate Diesel 1500-1999cc",
        "type": "Estate",
        "engine_type": "Diesel",
        "engine_cc_min": 1500,
        "engine_cc_max": 1999,
        "drive_type": "4WD",
        "average_initial_cost": 4000000,
        "fixed_cost_per_km": 49.83,
        "operating_cost_per_km": 27.33,
        "total_cost_per_km": 77.17,
        "fuel_cost_km": 15.77,
        "servicing_cost_km": 3.55,
        "repairs_cost_km": 5.33,
        "tyres_cost_km": 2.67,
        "annual_fixed_cost": 1495000,
        "annual_km": 30000
    },
    "4WD-D-3000A": {
        "name": "4WD Estate Diesel 2000-3000cc (A)",
        "type": "Estate",
        "engine_type": "Diesel",
        "engine_cc_min": 2000,
        "engine_cc_max": 3000,
        "drive_type": "4WD",
        "load_rating": "A",
        "average_initial_cost": 7500000,
        "fixed_cost_per_km": 90.52,
        "operating_cost_per_km": 43.58,
        "total_cost_per_km": 134.10,
        "fuel_cost_km": 21.92,
        "servicing_cost_km": 6.65,
        "repairs_cost_km": 10.00,
        "tyres_cost_km": 5.00,
        "annual_fixed_cost": 2715625,
        "annual_km": 30000
    },
    "4WD-D-3000B": {
        "name": "4WD Estate Diesel 2000-3000cc (B)",
        "type": "Estate",
        "engine_type": "Diesel",
        "engine_cc_min": 2000,
        "engine_cc_max": 3000,
        "drive_type": "4WD",
        "load_rating": "B",
        "average_initial_cost": 11500000,
        "fixed_cost_per_km": 137.02,
        "operating_cost_per_km": 47.91,
        "total_cost_per_km": 184.92,
        "fuel_cost_km": 21.92,
        "servicing_cost_km": 7.98,
        "repairs_cost_km": 12.00,
        "tyres_cost_km": 6.00,
        "annual_fixed_cost": 4110625,
        "annual_km": 30000
    },
    "4WD-D-4000": {
        "name": "4WD Estate Diesel 3001-4000cc",
        "type": "Estate",
        "engine_type": "Diesel",
        "engine_cc_min": 3001,
        "engine_cc_max": 4000,
        "drive_type": "4WD",
        "average_initial_cost": 10500000,
        "fixed_cost_per_km": 125.40,
        "operating_cost_per_km": 48.25,
        "total_cost_per_km": 173.65,
        "fuel_cost_km": 17.93,
        "servicing_cost_km": 9.31,
        "repairs_cost_km": 14.00,
        "tyres_cost_km": 7.00,
        "annual_fixed_cost": 3761875,
        "annual_km": 30000
    },
    "4WD-D-4000A": {
        "name": "4WD Estate Diesel Over 4000cc (A)",
        "type": "Estate",
        "engine_type": "Diesel",
        "engine_cc_min": 4001,
        "engine_cc_max": 9999,
        "drive_type": "4WD",
        "load_rating": "A",
        "average_initial_cost": 9000000,
        "fixed_cost_per_km": 107.96,
        "operating_cost_per_km": 61.39,
        "total_cost_per_km": 169.35,
        "fuel_cost_km": 28.19,
        "servicing_cost_km": 10.20,
        "repairs_cost_km": 15.33,
        "tyres_cost_km": 7.67,
        "annual_fixed_cost": 3238750,
        "annual_km": 30000
    },
    "4WD-D-4000B": {
        "name": "4WD Estate Diesel Over 4000cc (B)",
        "type": "Estate",
        "engine_type": "Diesel",
        "engine_cc_min": 4001,
        "engine_cc_max": 9999,
        "drive_type": "4WD",
        "load_rating": "B",
        "average_initial_cost": 15000000,
        "fixed_cost_per_km": 177.71,
        "operating_cost_per_km": 71.51,
        "total_cost_per_km": 249.22,
        "fuel_cost_km": 28.19,
        "servicing_cost_km": 13.30,
        "repairs_cost_km": 20.00,
        "tyres_cost_km": 10.00,
        "annual_fixed_cost": 5331250,
        "annual_km": 30000
    },
    # 2WD Pick-Up Petrol
    "PU-P-1000": {
        "name": "2WD Pick-Up Petrol Up to 1000cc",
        "type": "Pick-Up",
        "engine_type": "Petrol",
        "engine_cc_min": 0,
        "engine_cc_max": 1000,
        "drive_type": "2WD",
        "average_initial_cost": 1500000,
        "fixed_cost_per_km": 20.77,
        "operating_cost_per_km": 18.64,
        "total_cost_per_km": 39.42,
        "fuel_cost_km": 14.30,
        "servicing_cost_km": 1.33,
        "repairs_cost_km": 2.00,
        "tyres_cost_km": 1.00,
        "annual_fixed_cost": 623125,
        "annual_km": 30000
    },
    "PU-P-1400": {
        "name": "2WD Pick-Up Petrol 1001-1400cc",
        "type": "Pick-Up",
        "engine_type": "Petrol",
        "engine_cc_min": 1001,
        "engine_cc_max": 1400,
        "drive_type": "2WD",
        "average_initial_cost": 1950000,
        "fixed_cost_per_km": 26.00,
        "operating_cost_per_km": 21.58,
        "total_cost_per_km": 47.58,
        "fuel_cost_km": 15.93,
        "servicing_cost_km": 1.73,
        "repairs_cost_km": 2.60,
        "tyres_cost_km": 1.30,
        "annual_fixed_cost": 780063,
        "annual_km": 30000
    },
    "PU-P-1800": {
        "name": "2WD Pick-Up Petrol 1401-1800cc",
        "type": "Pick-Up",
        "engine_type": "Petrol",
        "engine_cc_min": 1401,
        "engine_cc_max": 1800,
        "drive_type": "2WD",
        "average_initial_cost": 2800000,
        "fixed_cost_per_km": 35.88,
        "operating_cost_per_km": 26.93,
        "total_cost_per_km": 62.81,
        "fuel_cost_km": 18.83,
        "servicing_cost_km": 2.48,
        "repairs_cost_km": 3.73,
        "tyres_cost_km": 1.87,
        "annual_fixed_cost": 1076500,
        "annual_km": 30000
    },
    "PU-P-2000": {
        "name": "2WD Pick-Up Petrol 1801-2000cc",
        "type": "Pick-Up",
        "engine_type": "Petrol",
        "engine_cc_min": 1801,
        "engine_cc_max": 2000,
        "drive_type": "2WD",
        "average_initial_cost": 2900000,
        "fixed_cost_per_km": 37.05,
        "operating_cost_per_km": 29.12,
        "total_cost_per_km": 66.17,
        "fuel_cost_km": 20.74,
        "servicing_cost_km": 2.57,
        "repairs_cost_km": 3.87,
        "tyres_cost_km": 1.93,
        "annual_fixed_cost": 1111375,
        "annual_km": 30000
    },
    "PU-P-3000": {
        "name": "2WD Pick-Up Petrol 2001-3000cc",
        "type": "Pick-Up",
        "engine_type": "Petrol",
        "engine_cc_min": 2001,
        "engine_cc_max": 3000,
        "drive_type": "2WD",
        "average_initial_cost": 2600000,
        "fixed_cost_per_km": 33.56,
        "operating_cost_per_km": 30.55,
        "total_cost_per_km": 64.11,
        "fuel_cost_km": 23.03,
        "servicing_cost_km": 2.31,
        "repairs_cost_km": 3.47,
        "tyres_cost_km": 1.73,
        "annual_fixed_cost": 1006750,
        "annual_km": 30000
    },
    # 2WD Pick-Up Diesel
    "PU-D-2000": {
        "name": "2WD Pick-Up Diesel 1500-2000cc",
        "type": "Pick-Up",
        "engine_type": "Diesel",
        "engine_cc_min": 1500,
        "engine_cc_max": 2000,
        "drive_type": "2WD",
        "average_initial_cost": 2700000,
        "fixed_cost_per_km": 34.72,
        "operating_cost_per_km": 25.73,
        "total_cost_per_km": 60.44,
        "fuel_cost_km": 17.93,
        "servicing_cost_km": 2.39,
        "repairs_cost_km": 3.60,
        "tyres_cost_km": 1.80,
        "annual_fixed_cost": 1041625,
        "annual_km": 30000
    },
    # 4WD Pick-Up Diesel
    "4WD-PU-D-3000": {
        "name": "4WD Pick-Up Diesel 2000-3000cc",
        "type": "Pick-Up",
        "engine_type": "Diesel",
        "engine_cc_min": 2000,
        "engine_cc_max": 3000,
        "drive_type": "4WD",
        "average_initial_cost": 3500000,
        "fixed_cost_per_km": 44.02,
        "operating_cost_per_km": 38.31,
        "total_cost_per_km": 82.33,
        "fuel_cost_km": 28.19,
        "servicing_cost_km": 3.10,
        "repairs_cost_km": 4.67,
        "tyres_cost_km": 2.33,
        "annual_fixed_cost": 1320625,
        "annual_km": 30000
    },
    "4WD-PU-D-3001": {
        "name": "4WD Pick-Up Diesel Over 3000cc",
        "type": "Pick-Up",
        "engine_type": "Diesel",
        "engine_cc_min": 3001,
        "engine_cc_max": 9999,
        "drive_type": "4WD",
        "average_initial_cost": 3900000,
        "fixed_cost_per_km": 48.67,
        "operating_cost_per_km": 41.62,
        "total_cost_per_km": 90.30,
        "fuel_cost_km": 30.35,
        "servicing_cost_km": 3.46,
        "repairs_cost_km": 5.20,
        "tyres_cost_km": 2.60,
        "annual_fixed_cost": 1460125,
        "annual_km": 30000
    },
    # 4WD DCAB Pick-Up
    "4WD-DCAB-P-3000": {
        "name": "4WD DCAB Pick-Up Petrol 2000-3000cc",
        "type": "Pick-Up",
        "engine_type": "Petrol",
        "engine_cc_min": 2000,
        "engine_cc_max": 3000,
        "drive_type": "4WD",
        "average_initial_cost": 3600000,
        "fixed_cost_per_km": 45.18,
        "operating_cost_per_km": 34.81,
        "total_cost_per_km": 79.99,
        "fuel_cost_km": 24.40,
        "servicing_cost_km": 3.19,
        "repairs_cost_km": 4.80,
        "tyres_cost_km": 2.40,
        "annual_fixed_cost": 1355500,
        "annual_km": 30000
    },
    "4WD-DCAB-D-3000": {
        "name": "4WD DCAB Pick-Up Diesel 2000-3000cc",
        "type": "Pick-Up",
        "engine_type": "Diesel",
        "engine_cc_min": 2000,
        "engine_cc_max": 3000,
        "drive_type": "4WD",
        "average_initial_cost": 3600000,
        "fixed_cost_per_km": 45.18,
        "operating_cost_per_km": 34.79,
        "total_cost_per_km": 79.96,
        "fuel_cost_km": 24.67,
        "servicing_cost_km": 3.10,
        "repairs_cost_km": 4.67,
        "tyres_cost_km": 2.33,
        "annual_fixed_cost": 1355500,
        "annual_km": 30000
    },
    "4WD-DCAB-D-3001": {
        "name": "4WD DCAB Pick-Up Diesel Over 3000cc",
        "type": "Pick-Up",
        "engine_type": "Diesel",
        "engine_cc_min": 3001,
        "engine_cc_max": 9999,
        "drive_type": "4WD",
        "average_initial_cost": 4800000,
        "fixed_cost_per_km": 59.13,
        "operating_cost_per_km": 41.96,
        "total_cost_per_km": 101.10,
        "fuel_cost_km": 30.13,
        "servicing_cost_km": 3.64,
        "repairs_cost_km": 5.47,
        "tyres_cost_km": 2.73,
        "annual_fixed_cost": 1774000,
        "annual_km": 30000
    },
    # Commercial Vehicles
    "TRUCK-3T": {
        "name": "3 Ton Truck",
        "type": "Truck",
        "engine_type": "Diesel",
        "drive_type": "2WD",
        "average_initial_cost": 4100000,
        "fixed_cost_per_km": 51.00,
        "operating_cost_per_km": 37.59,
        "total_cost_per_km": 88.59,
        "fuel_cost_km": 26.04,
        "servicing_cost_km": 3.55,
        "repairs_cost_km": 5.33,
        "tyres_cost_km": 2.67,
        "annual_fixed_cost": 1529875,
        "annual_km": 30000
    },
    "TRUCK-5T": {
        "name": "5 Ton Truck",
        "type": "Truck",
        "engine_type": "Diesel",
        "drive_type": "2WD",
        "average_initial_cost": 4800000,
        "fixed_cost_per_km": 59.13,
        "operating_cost_per_km": 40.19,
        "total_cost_per_km": 99.33,
        "fuel_cost_km": 26.32,
        "servicing_cost_km": 4.26,
        "repairs_cost_km": 6.40,
        "tyres_cost_km": 3.20,
        "annual_fixed_cost": 1774000,
        "annual_km": 30000
    },
    "TRUCK-7T": {
        "name": "7 Ton Truck",
        "type": "Truck",
        "engine_type": "Diesel",
        "drive_type": "2WD",
        "average_initial_cost": 6500000,
        "fixed_cost_per_km": 78.90,
        "operating_cost_per_km": 40.55,
        "total_cost_per_km": 119.45,
        "fuel_cost_km": 24.67,
        "servicing_cost_km": 4.88,
        "repairs_cost_km": 7.33,
        "tyres_cost_km": 3.67,
        "annual_fixed_cost": 2366927,
        "annual_km": 30000
    },
    "TRUCK-9T": {
        "name": "9 Ton Truck",
        "type": "Truck",
        "engine_type": "Diesel",
        "drive_type": "2WD",
        "average_initial_cost": 6500000,
        "fixed_cost_per_km": 78.90,
        "operating_cost_per_km": 50.78,
        "total_cost_per_km": 129.68,
        "fuel_cost_km": 32.88,
        "servicing_cost_km": 4.88,
        "repairs_cost_km": 8.67,
        "tyres_cost_km": 4.33,
        "annual_fixed_cost": 2366927,
        "annual_km": 30000
    },
    "MINIBUS": {
        "name": "Mini-Bus 2000-3000cc",
        "type": "Mini-Bus",
        "engine_type": "Diesel",
        "engine_cc_min": 2000,
        "engine_cc_max": 3000,
        "drive_type": "2WD",
        "average_initial_cost": 4800000,
        "fixed_cost_per_km": 59.13,
        "operating_cost_per_km": 48.78,
        "total_cost_per_km": 107.91,
        "fuel_cost_km": 32.88,
        "servicing_cost_km": 4.88,
        "repairs_cost_km": 7.33,
        "tyres_cost_km": 3.67,
        "annual_fixed_cost": 1774000,
        "annual_km": 30000
    }
}

# Depreciation by age (percentage of value remaining)
DEPRECIATION_BY_AGE = {
    0: 1.00,  # New
    1: 0.85,  # 1 year old
    2: 0.73,  # 2 years old
    3: 0.63,  # 3 years old
    4: 0.55,  # 4 years old
    5: 0.48,  # 5 years old
    6: 0.42,  # 6 years old
    7: 0.36,  # 7 years old
    8: 0.31,  # 8 years old
    9: 0.27,  # 9 years old
    10: 0.23, # 10 years old
}


# ─── Mileage Service ──────────────────────────────────────────

class MileageService:
    """Service for mileage rate calculations and cost analysis"""
    
    def __init__(self):
        self.categories = VEHICLE_CATEGORIES
        self.depreciation = DEPRECIATION_BY_AGE
    
    def get_category(self, engine_type: str, engine_cc: int, 
                     drive_type: str = "2WD", load_rating: str = None) -> Optional[Dict]:
        """
        Get vehicle category based on specifications.
        
        Args:
            engine_type: Petrol, Diesel, Electric, Hybrid
            engine_cc: Engine capacity in cubic centimeters
            drive_type: 2WD, 4WD, AWD
            load_rating: A, B, or None
            
        Returns:
            Category data or None
        """
        # Build search keys
        search_key = None
        
        if engine_type == "Petrol":
            if engine_cc <= 850:
                search_key = "PS-850"
            elif engine_cc <= 1050:
                search_key = "PS-1050"
            elif engine_cc <= 1250:
                search_key = "PS-1250"
            elif engine_cc <= 1350:
                search_key = "PS-1350"
            elif engine_cc <= 1500:
                search_key = "PS-1500"
            elif engine_cc <= 1650:
                search_key = "PS-1650"
            elif engine_cc <= 1850:
                search_key = f"PS-1850{load_rating or 'A'}"
            elif engine_cc <= 2000:
                search_key = f"PS-2000{load_rating or 'A'}"
            elif engine_cc <= 2300:
                search_key = f"PS-2300{load_rating or 'A'}"
            elif engine_cc <= 2600:
                search_key = "PS-2600"
            else:
                search_key = "PS-2601"
        
        elif engine_type == "Diesel":
            if engine_cc <= 1450:
                search_key = "DS-1450"
            elif engine_cc <= 2000:
                search_key = "DS-2000"
            else:
                search_key = "DS-2000"  # Fallback
        
        # Check if key exists
        return self.categories.get(search_key)
    
    def calculate_mileage_rate(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate mileage rate for a vehicle.
        
        Args:
            vehicle_data: Vehicle details (make, model, year, engine_type, engine_cc, etc.)
            
        Returns:
            Mileage rate calculation results
        """
        engine_type = vehicle_data.get('engine_type', 'Petrol')
        engine_cc = vehicle_data.get('engine_cc', 1500)
        drive_type = vehicle_data.get('drive_type', '2WD')
        load_rating = vehicle_data.get('load_rating')
        annual_km = vehicle_data.get('annual_km', 30000)
        vehicle_age = vehicle_data.get('vehicle_age', 1)
        
        # Get category
        category = self.get_category(engine_type, engine_cc, drive_type, load_rating)
        
        if not category:
            # Default to a common category
            category = self.categories.get("PS-1500")
            if not category:
                raise ValueError("No matching vehicle category found")
        
        # Calculate costs
        annual_fixed_cost = category.get('fixed_cost_per_km', 0) * annual_km
        annual_operating_cost = category.get('operating_cost_per_km', 0) * annual_km
        annual_total_cost = annual_fixed_cost + annual_operating_cost
        
        # Apply age adjustment to fixed costs (depreciation reduces over time)
        age_factor = self.depreciation.get(vehicle_age, 0.50)
        adjusted_fixed_cost = category.get('fixed_cost_per_km', 0) * age_factor
        
        # Calculate fuel efficiency (approx)
        fuel_efficiency = self._calculate_fuel_efficiency(engine_type, engine_cc)
        
        return {
            "vehicle": {
                "engine_type": engine_type,
                "engine_cc": engine_cc,
                "drive_type": drive_type,
                "load_rating": load_rating,
                "category": category.get('name'),
                "category_code": category.get('code', 'UNKNOWN')
            },
            "mileage_rates": {
                "fixed_cost_per_km": round(category.get('fixed_cost_per_km', 0), 2),
                "operating_cost_per_km": round(category.get('operating_cost_per_km', 0), 2),
                "total_cost_per_km": round(category.get('total_cost_per_km', 0), 2),
                "adjusted_fixed_cost_per_km": round(adjusted_fixed_cost, 2),
                "currency": "KES"
            },
            "annual_costs": {
                "fixed_cost": round(annual_fixed_cost, 2),
                "operating_cost": round(annual_operating_cost, 2),
                "total_cost": round(annual_total_cost, 2),
                "annual_km": annual_km,
                "vehicle_age": vehicle_age
            },
            "breakdown": {
                "fuel_cost_km": round(category.get('fuel_cost_km', 0), 2),
                "servicing_cost_km": round(category.get('servicing_cost_km', 0), 2),
                "repairs_cost_km": round(category.get('repairs_cost_km', 0), 2),
                "tyres_cost_km": round(category.get('tyres_cost_km', 0), 2),
                "depreciation_factor": age_factor
            },
            "fuel_economy": fuel_efficiency,
            "timestamp": datetime.now().isoformat()
        }
    
    def calculate_trip_cost(self, distance_km: float, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate cost for a specific trip.
        
        Args:
            distance_km: Distance in kilometers
            vehicle_data: Vehicle details
            
        Returns:
            Trip cost calculation
        """
        # Get mileage rate
        mileage = self.calculate_mileage_rate(vehicle_data)
        rate_per_km = mileage['mileage_rates']['total_cost_per_km']
        
        trip_cost = distance_km * rate_per_km
        fuel_cost = distance_km * mileage['breakdown']['fuel_cost_km']
        
        return {
            "trip": {
                "distance_km": distance_km,
                "duration_minutes": distance_km * 2  # Approximate: 30 km/h average
            },
            "costs": {
                "total_cost": round(trip_cost, 2),
                "fuel_cost": round(fuel_cost, 2),
                "rate_per_km": rate_per_km,
                "currency": "KES"
            },
            "breakdown": {
                "distance": distance_km,
                "rate_per_km": rate_per_km,
                "fuel_rate_per_km": mileage['breakdown']['fuel_cost_km']
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def calculate_fleet_mileage(self, fleet_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate mileage rates for a fleet of vehicles.
        
        Args:
            fleet_data: List of vehicle data
            
        Returns:
            Fleet mileage analysis
        """
        results = []
        total_cost = 0
        total_fixed_cost = 0
        total_operating_cost = 0
        total_km = 0
        
        for vehicle in fleet_data:
            try:
                result = self.calculate_mileage_rate(vehicle)
                results.append(result)
                
                total_cost += result['annual_costs']['total_cost']
                total_fixed_cost += result['annual_costs']['fixed_cost']
                total_operating_cost += result['annual_costs']['operating_cost']
                total_km += result['annual_costs']['annual_km']
            except Exception as e:
                logger.warning(f"Error calculating mileage for vehicle: {e}")
        
        return {
            "fleet": {
                "total_vehicles": len(results),
                "total_annual_km": round(total_km, 2),
                "total_annual_cost": round(total_cost, 2),
                "total_fixed_cost": round(total_fixed_cost, 2),
                "total_operating_cost": round(total_operating_cost, 2),
                "average_cost_per_km": round(total_cost / total_km if total_km > 0 else 0, 2)
            },
            "vehicles": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_fuel_efficiency(self, engine_type: str, engine_cc: int) -> Dict[str, Any]:
        """Calculate approximate fuel efficiency based on engine specs."""
        # Simplified fuel efficiency calculation
        if engine_type == "Electric":
            return {
                "efficiency": "4.5 km/kWh",
                "range_km": 300,
                "cost_per_km": 2.00,
                "type": "Electric"
            }
        elif engine_type == "Hybrid":
            if engine_cc <= 1500:
                return {"efficiency": "22 km/L", "type": "Hybrid", "cost_per_km": 6.00}
            else:
                return {"efficiency": "18 km/L", "type": "Hybrid", "cost_per_km": 7.00}
        elif engine_type == "Diesel":
            if engine_cc <= 1500:
                return {"efficiency": "18 km/L", "type": "Diesel", "cost_per_km": 8.50}
            elif engine_cc <= 2500:
                return {"efficiency": "14 km/L", "type": "Diesel", "cost_per_km": 10.50}
            else:
                return {"efficiency": "10 km/L", "type": "Diesel", "cost_per_km": 14.00}
        else:  # Petrol
            if engine_cc <= 1000:
                return {"efficiency": "15 km/L", "type": "Petrol", "cost_per_km": 7.50}
            elif engine_cc <= 1500:
                return {"efficiency": "13 km/L", "type": "Petrol", "cost_per_km": 8.50}
            elif engine_cc <= 2000:
                return {"efficiency": "10 km/L", "type": "Petrol", "cost_per_km": 11.00}
            elif engine_cc <= 3000:
                return {"efficiency": "8 km/L", "type": "Petrol", "cost_per_km": 14.00}
            else:
                return {"efficiency": "6 km/L", "type": "Petrol", "cost_per_km": 18.00}
    
    def get_comparison(self, vehicle1: Dict, vehicle2: Dict) -> Dict[str, Any]:
        """
        Compare mileage rates between two vehicles.
        
        Args:
            vehicle1: First vehicle data
            vehicle2: Second vehicle data
            
        Returns:
            Comparison results
        """
        rate1 = self.calculate_mileage_rate(vehicle1)
        rate2 = self.calculate_mileage_rate(vehicle2)
        
        diff_per_km = rate1['mileage_rates']['total_cost_per_km'] - rate2['mileage_rates']['total_cost_per_km']
        diff_annual = rate1['annual_costs']['total_cost'] - rate2['annual_costs']['total_cost']
        
        return {
            "vehicle1": {
                "name": f"{vehicle1.get('make', 'Unknown')} {vehicle1.get('model', 'Unknown')}",
                "rate": rate1['mileage_rates'],
                "annual": rate1['annual_costs']
            },
            "vehicle2": {
                "name": f"{vehicle2.get('make', 'Unknown')} {vehicle2.get('model', 'Unknown')}",
                "rate": rate2['mileage_rates'],
                "annual": rate2['annual_costs']
            },
            "difference": {
                "per_km": round(diff_per_km, 2),
                "annual": round(diff_annual, 2),
                "percentage": round((diff_per_km / rate2['mileage_rates']['total_cost_per_km']) * 100 if rate2['mileage_rates']['total_cost_per_km'] > 0 else 0, 2),
                "more_efficient": vehicle2.get('model', 'Vehicle 2') if diff_per_km > 0 else vehicle1.get('model', 'Vehicle 1')
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_multi_year_comparison(self, vehicle_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get mileage rates for a vehicle over multiple years.
        
        Args:
            vehicle_data: Vehicle details
            
        Returns:
            Multi-year comparison
        """
        results = []
        
        for age in range(0, 6):
            data = vehicle_data.copy()
            data['vehicle_age'] = age
            result = self.calculate_mileage_rate(data)
            results.append({
                "age": age,
                "total_cost_per_km": result['mileage_rates']['total_cost_per_km'],
                "fixed_cost_per_km": result['mileage_rates']['fixed_cost_per_km'],
                "operating_cost_per_km": result['mileage_rates']['operating_cost_per_km'],
                "annual_total": result['annual_costs']['total_cost']
            })
        
        return results


# ─── Singleton Instance ──────────────────────────────────────

mileage_service = MileageService()


# ─── Exports ────────────────────────────────────────────────────

__all__ = [
    'mileage_service',
    'MileageService',
    'VEHICLE_CATEGORIES',
    'DEPRECIATION_BY_AGE'
]
