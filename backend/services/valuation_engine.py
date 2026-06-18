import math
import random
from datetime import datetime

def calculate_valuation(vehicle_data):
    make = vehicle_data.get('make', 'Toyota')
    model = vehicle_data.get('model', 'Axio')
    year = int(vehicle_data.get('year', 2020))
    odometer = int(vehicle_data.get('odometer', 50000))
    condition = vehicle_data.get('condition', 'Good')
    accident = vehicle_data.get('accident_history', 'None')

    base_prices = {
        'toyota': 2800000,
        'honda': 2500000,
        'nissan': 2300000,
        'mercedes': 5000000,
        'bmw': 4500000,
        'audi': 4200000,
        'volkswagen': 2400000,
        'ford': 2100000,
        'subaru': 2600000,
        'mazda': 2200000,
        'mitsubishi': 2100000,
        'isuzu': 2800000,
        'land rover': 6000000,
        'jaguar': 5500000,
        'lexus': 4800000,
        'volvo': 3500000,
        'hyundai': 2000000,
        'kia': 1900000,
        'suzuki': 1800000,
        'other': 2000000
    }
    base_value = base_prices.get(make.lower(), 2000000)

    current_year = 2026
    age = current_year - year
    age_factor = max(0.35, 1 - age * 0.08)

    expected_mileage = max(age * 15000, 1)
    mileage_ratio = odometer / expected_mileage
    if mileage_ratio <= 0.8:
        mileage_factor = 1.05
    elif mileage_ratio <= 1.0:
        mileage_factor = 1.0
    elif mileage_ratio <= 1.2:
        mileage_factor = 0.92
    elif mileage_ratio <= 1.5:
        mileage_factor = 0.82
    elif mileage_ratio <= 2.0:
        mileage_factor = 0.70
    else:
        mileage_factor = 0.55

    condition_factors = {
        'Excellent': 1.15,
        'Very Good': 1.0,
        'Good': 0.85,
        'Fair': 0.70,
        'Poor': 0.50
    }
    condition_factor = condition_factors.get(condition, 0.85)

    accident_factors = {
        'None': 1.0,
        'Minor': 0.85,
        'Moderate': 0.65,
        'Major': 0.40
    }
    accident_factor = accident_factors.get(accident, 1.0)

    market_adjustment = 0.95 + 0.1 * random.random()

    market_value = base_value * age_factor * mileage_factor * condition_factor * accident_factor * market_adjustment
    market_value = max(100000, min(market_value, base_value * 1.2))
    market_value = round(market_value / 1000) * 1000

    return {
        'market_value': market_value,
        'insurance_value': round(market_value * 1.1),
        'trade_in_value': round(market_value * 0.8),
        'forced_sale_value': round(market_value * 0.7),
        'valuation_date': datetime.now().isoformat(),
        'factors_used': {
            'base_value': base_value,
            'age_factor': age_factor,
            'mileage_factor': mileage_factor,
            'condition_factor': condition_factor,
            'accident_factor': accident_factor,
            'market_adjustment': market_adjustment
        }
    }
