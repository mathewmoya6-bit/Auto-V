def calculate_mileage_rate(vehicle_data):
    """
    Calculate mileage reimbursement rate based on total cost of ownership.
    Returns rate per km and breakdown.
    """
    purchase_price = vehicle_data['purchase_price']
    residual_value = vehicle_data['residual_value']
    annual_km = vehicle_data['annual_km']
    fuel_economy = vehicle_data.get('fuel_economy') or get_default_fuel_economy(
        vehicle_data['make'], vehicle_data['model'], vehicle_data['engine_capacity']
    )
    fuel_type = vehicle_data['fuel_type']
    insurance = vehicle_data['insurance_cost']
    service = vehicle_data['service_cost']
    repairs = vehicle_data['repair_cost']
    tyres = vehicle_data['tyre_cost']
    tyre_life = vehicle_data['tyre_life']
    licence = vehicle_data['licence_cost']
    finance = vehicle_data['finance_cost']
    dep_rate = vehicle_data['depreciation_rate']
    risk_reserve = vehicle_data['risk_reserve']
    
    # Depreciation
    annual_depreciation = (purchase_price - residual_value) * dep_rate
    
    # Fuel cost
    fuel_prices = {'petrol': 199.15, 'diesel': 185.00, 'hybrid': 199.15, 'electric': 0, 'lpg': 120.00}
    fuel_price = fuel_prices.get(fuel_type, 199.15)
    if fuel_type == 'electric':
        annual_fuel_cost = annual_km * 10  # ~10 KES/km for electric
    else:
        annual_fuel_cost = (annual_km / fuel_economy) * fuel_price
    
    # Tyre cost (annualized)
    annual_tyre_cost = (tyres / tyre_life) * annual_km
    
    # Factors
    factors = {
        'journey_purpose': {'business': 1.0, 'ngo': 0.95, 'government': 0.90, 'private': 1.0, 'fleet': 0.92},
        'road_condition': {'highway': 0.85, 'mixed': 1.0, 'urban': 1.10, 'rural': 0.95, 'offroad': 1.25},
        'location': {'nairobi': 1.05, 'mombasa': 1.02, 'kisumu': 1.0, 'nakuru': 0.98, 'eldoret': 0.97, 'rural': 0.92},
        'driver_behaviour': {'conservative': 0.90, 'normal': 1.0, 'aggressive': 1.12},
        'maintenance_quality': {'dealer': 1.15, 'independent': 1.0, 'poor': 1.30}
    }
    
    purpose = vehicle_data.get('journey_purpose', 'business')
    road = vehicle_data.get('road_condition', 'mixed')
    location = vehicle_data.get('location', 'nairobi')
    driver = vehicle_data.get('driver_behaviour', 'normal')
    maintenance = vehicle_data.get('maintenance_quality', 'independent')
    
    combined_factor = (
        factors['journey_purpose'].get(purpose, 1.0) *
        factors['road_condition'].get(road, 1.0) *
        factors['location'].get(location, 1.0) *
        factors['driver_behaviour'].get(driver, 1.0) *
        factors['maintenance_quality'].get(maintenance, 1.0)
    )
    
    adjusted_fuel = annual_fuel_cost * combined_factor
    adjusted_tyre = annual_tyre_cost * combined_factor
    adjusted_service = service * combined_factor
    adjusted_repair = repairs * combined_factor
    
    total_before_reserve = (annual_depreciation + adjusted_fuel + adjusted_tyre +
                           adjusted_service + insurance + licence + adjusted_repair + finance)
    reserve_amount = total_before_reserve * risk_reserve
    total_annual_cost = total_before_reserve + reserve_amount
    rate_per_km = total_annual_cost / annual_km
    rate_per_mile = rate_per_km * 1.60934
    
    return {
        'rate_per_km': rate_per_km,
        'rate_per_mile': rate_per_mile,
        'total_annual_cost': total_annual_cost,
        'monthly_cost': total_annual_cost / 12,
        'fuel_cost_per_year': adjusted_fuel,
        'depreciation_per_year': annual_depreciation,
        'risk_reserve_percent': risk_reserve * 100,
        'breakdown': {
            'depreciation': annual_depreciation,
            'fuel': adjusted_fuel,
            'service': adjusted_service,
            'tyres': adjusted_tyre,
            'insurance': insurance,
            'licence': licence,
            'repairs': adjusted_repair,
            'finance': finance,
            'risk_reserve': reserve_amount
        },
        'combined_factor': combined_factor,
        'vehicle_data': {
            'make': vehicle_data.get('make'),
            'model': vehicle_data.get('model'),
            'year': vehicle_data.get('year'),
            'fuel_type': fuel_type,
            'purchase_price': purchase_price
        }
    }

def get_default_fuel_economy(make, model, engine_cc):
    """Return default fuel economy based on make/model/engine."""
    # Simplified lookup
    if make.lower() == 'toyota':
        if model.lower() in ['axio', 'corolla']:
            return 16
        elif model.lower() == 'land cruiser':
            return 8
        else:
            return 14
    else:
        return 13
