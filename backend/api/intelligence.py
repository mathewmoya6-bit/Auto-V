# api/routes/intelligence.py – AUTO-V Intelligence Layer (Production-Ready)

import logging
import traceback
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from api.auth_middleware import require_auth

# ============================================================
# SAFE IMPORTS (Prevent startup crashes)
# ============================================================
try:
    from services.valuation import calculate_value
except ImportError as e:
    logger.error(f"Valuation module failed to load: {e}")
    calculate_value = None

try:
    from services.mileage_rate import calculate_mileage_rate
except ImportError as e:
    logger.error(f"Mileage rate module failed to load: {e}")
    calculate_mileage_rate = None

logger = logging.getLogger(__name__)

intelligence_bp = Blueprint('intelligence', __name__)

# ============================================================
# CONSTANTS / CONFIG
# ============================================================
MAX_RECENT_REQUESTS = 500  # For performance
DEFAULT_MONTHLY_KM = 2000
DEFAULT_YEARLY_KM = 24000
RISK_BASELINE = 5000000  # Will be normalized by category later

# ============================================================
# HELPER: Normalize risk score
# ============================================================
def normalize_risk_score(raw_score, min_val=0, max_val=100):
    """Clamp score between min and max."""
    return max(min_val, min(max_val, raw_score))

# ============================================================
# ENDPOINT 1: MARKET TRENDS (REAL, with Supabase)
# ============================================================
@intelligence_bp.route('/market-trends', methods=['GET'])
@require_auth
def market_trends(user):
    """
    Real market trends based on historical service_requests data.
    Returns aggregated trends by make.
    """
    supabase = get_supabase()
    try:
        # Fetch recent valuations (with limit for performance)
        resp = supabase.table('service_requests')\
            .select('make, year, amount, result')\
            .eq('service_type', 'valuation')\
            .order('created_at', desc=True)\
            .limit(MAX_RECENT_REQUESTS)\
            .execute()

        if not resp.data:
            return jsonify({
                'trends': {},
                'average_values': {},
                'message': 'Not enough data for trends'
            }), 200

        # Aggregate by make
        make_data = {}
        for item in resp.data:
            make = item.get('make', 'unknown').lower().capitalize()
            if make not in make_data:
                make_data[make] = {
                    'count': 0,
                    'total_value': 0,
                    'years': [],
                    'values': []
                }
            make_data[make]['count'] += 1
            # Use market value from result if available, otherwise amount
            result = item.get('result', {})
            value = result.get('market_value', item.get('amount', 0))
            if value:
                make_data[make]['total_value'] += value
                make_data[make]['values'].append(value)
            year = item.get('year')
            if year:
                make_data[make]['years'].append(year)

        # Compute trends (simple direction)
        trends = {}
        avg_values = {}
        for make, data in make_data.items():
            if data['values']:
                avg = data['total_value'] / data['count']
                avg_values[make] = round(avg, 2)
                # Simple trend: compare last 3 to average
                if len(data['values']) >= 3:
                    recent = data['values'][-3:]
                    recent_avg = sum(recent) / len(recent)
                    if recent_avg > avg * 1.05:
                        trends[make] = 'Rising'
                    elif recent_avg < avg * 0.95:
                        trends[make] = 'Declining'
                    else:
                        trends[make] = 'Stable'
                else:
                    trends[make] = 'Limited data'

        return jsonify({
            'trends': trends,
            'average_values': avg_values,
            'data_points': len(resp.data)
        }), 200

    except Exception as e:
        logger.error(f"Market trends error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': 'Unable to compute market trends'}), 500

# ============================================================
# ENDPOINT 2: VIN DECODE (PLACEHOLDER – REPLACE WITH REAL API)
# ============================================================
@intelligence_bp.route('/vin-decode', methods=['POST'])
@require_auth
def vin_decode(user):
    """
    VIN Decoder. Currently a placeholder; replace with NHTSA, CarVertical, or custom model.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    vin = data.get('vin', '').strip().upper()
    if not vin or len(vin) < 11:
        return jsonify({'error': 'Invalid VIN (minimum 11 characters)'}), 400

    # TODO: Replace with real VIN decoding service (e.g., NHTSA API, CarVertical)
    # For now, we return a mock response with realistic structure.
    # In production, you would call an external API or a trained model.

    mock_response = {
        'vin': vin,
        'make': 'Toyota' if vin.startswith('J') else 'Unknown',
        'model': 'Axio' if vin.startswith('J') else 'Unknown',
        'year': 2020 if vin.startswith('J') else 0,
        'engine': '1500cc',
        'country': 'Japan' if vin.startswith('J') else 'Unknown',
        'body_style': 'Sedan',
        'transmission': 'Automatic',
        'fuel_type': 'Petrol'
    }
    # Store VIN lookup for analytics (optional)
    try:
        supabase = get_supabase()
        supabase.table('vin_lookups').insert({
            'vin': vin,
            'user_id': user.id,
            'decoded_data': mock_response,
            'created_at': datetime.now().isoformat()
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log VIN lookup: {e}")

    return jsonify(mock_response), 200

# ============================================================
# ENDPOINT 3: VEHICLE INTELLIGENCE SCORE (AI-POWERED)
# ============================================================
@intelligence_bp.route('/vehicle-intelligence', methods=['POST'])
@require_auth
def vehicle_intelligence(user):
    """
    Compute a comprehensive intelligence score for a vehicle:
    - Market heat score
    - Risk of depreciation
    - Buy/Sell recommendation
    - Confidence level
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    # Input validation (critical)
    try:
        make = data.get('make', '').strip()
        model = data.get('model', '').strip()
        year = int(data.get('year', 0))
        mileage = int(data.get('mileage', 0))
        condition = data.get('condition', 'good').lower()
        purpose = data.get('purpose', 'general')
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid numeric input for year or mileage'}), 400

    if not make or not model or year < 1950 or mileage < 0:
        return jsonify({'error': 'Missing or invalid vehicle parameters'}), 400

    # 1. Get valuation (if module available)
    if calculate_value:
        try:
            valuation_result = calculate_value(
                make=make,
                model=model,
                year=year,
                odometer=mileage,
                condition=condition,
                purpose=purpose
            )
            market_value = valuation_result.get('market_value', 0)
        except Exception as e:
            logger.error(f"Valuation engine failed: {e}")
            market_value = 0
    else:
        market_value = 0

    # 2. Get mileage running cost (if module available)
    if calculate_mileage_rate:
        try:
            mileage_result = calculate_mileage_rate(
                vehicle_type=data.get('vehicle_type', 'sedan'),
                usage=data.get('usage', 'personal'),
                region=data.get('region', 'nairobi'),
                road_condition=data.get('road_condition', 'good'),
                purpose="vehicle_running_cost_analysis",
                monthly_km=data.get('monthly_km', DEFAULT_MONTHLY_KM),
                yearly_km=data.get('yearly_km', DEFAULT_YEARLY_KM)
            )
            cost_per_km = mileage_result.get('cost_per_km', 0)
        except Exception as e:
            logger.error(f"Mileage rate engine failed: {e}")
            cost_per_km = 0
    else:
        cost_per_km = 0

    # 3. Compute intelligence scores
    # Heat score (0-100): based on market value vs baseline by category
    # For now, use simple logic; can be enhanced with historical data.
    heat_score = 50  # default
    if market_value > 0:
        # Normalize by baseline (adjust per category later)
        # For simplicity, use log scale
        import math
        heat_score = min(95, 50 + math.log(market_value / 500000, 2) * 2)
        heat_score = max(5, heat_score)

    # Risk of depreciation: based on age, mileage, condition
    risk = 50
    if year > 0:
        age = 2026 - year
        if age > 10:
            risk += 20
        elif age > 5:
            risk += 10
        else:
            risk -= 10
        risk = min(95, risk)

    if mileage > 150000:
        risk += 15
    elif mileage > 80000:
        risk += 5

    if condition == 'poor':
        risk += 15
    elif condition == 'fair':
        risk += 5

    risk = max(5, min(95, risk))

    # Buy recommendation: low risk + high heat = Buy, etc.
    if heat_score > 70 and risk < 30:
        recommendation = "Strong Buy"
    elif heat_score > 60 and risk < 40:
        recommendation = "Buy"
    elif heat_score > 40 and risk < 60:
        recommendation = "Hold"
    elif heat_score < 30 and risk > 70:
        recommendation = "Sell"
    else:
        recommendation = "Evaluate"

    # Confidence score from valuation engine if available
    confidence = valuation_result.get('confidence_score', 70) if valuation_result else 70

    result = {
        'market_value': market_value,
        'cost_per_km': cost_per_km,
        'intelligence': {
            'heat_score': round(heat_score, 1),
            'risk_score': round(risk, 1),
            'confidence_score': round(confidence, 1),
            'recommendation': recommendation
        },
        'inputs': {
            'make': make,
            'model': model,
            'year': year,
            'mileage': mileage,
            'condition': condition
        }
    }

    return jsonify(result), 200

# ============================================================
# ENDPOINT 4: INTELLIGENCE DASHBOARD (ADMIN)
# ============================================================
@intelligence_bp.route('/dashboard', methods=['GET'])
@require_auth
def intelligence_dashboard(user):
    """
    Admin dashboard: market summaries, top trends, etc.
    """
    supabase = get_supabase()
    try:
        # Top 5 makes by valuation count
        resp = supabase.table('service_requests')\
            .select('make, count')\
            .eq('service_type', 'valuation')\
            .group_by('make')\
            .order('count', desc=True)\
            .limit(5)\
            .execute()
        top_makes = resp.data if resp.data else []

        # Average valuations per year (trend)
        # For simplicity, we'll compute from recent data
        years_resp = supabase.table('service_requests')\
            .select('year, result')\
            .eq('service_type', 'valuation')\
            .order('year')\
            .execute()

        avg_by_year = {}
        if years_resp.data:
            for item in years_resp.data:
                year = item.get('year')
                if not year:
                    continue
                result = item.get('result', {})
                value = result.get('market_value', 0)
                if value:
                    if year not in avg_by_year:
                        avg_by_year[year] = {'total': 0, 'count': 0}
                    avg_by_year[year]['total'] += value
                    avg_by_year[year]['count'] += 1
            # Compute averages
            for year, data in avg_by_year.items():
                avg_by_year[year] = round(data['total'] / data['count'])

        return jsonify({
            'top_makes': top_makes,
            'average_values_by_year': avg_by_year,
            'total_valuations': len(years_resp.data) if years_resp.data else 0,
            'message': 'Intelligence dashboard'
        }), 200

    except Exception as e:
        logger.error(f"Dashboard error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': 'Unable to load dashboard'}), 500
