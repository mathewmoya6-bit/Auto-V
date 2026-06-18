# api/intelligence.py – AUTO-V Intelligence Layer (FULLY FIXED)

# ─── LOGGER MUST BE DEFINED FIRST ──────────────────────────
import logging
logger = logging.getLogger(__name__)

# ─── NOW SAFE TO IMPORT OTHER MODULES ──────────────────────
import traceback
import math
from datetime import datetime
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from api.auth_middleware import require_auth

# ─── SAFE IMPORTS (logger is now defined) ──────────────────
try:
    from services.valuation_engine import calculate_value
except ImportError as e:
    logger.error(f"Valuation module failed to load: {e}")
    calculate_value = None

try:
    from services.mileage_rate import calculate_mileage_rate
except ImportError as e:
    logger.error(f"Mileage rate module failed to load: {e}")
    calculate_mileage_rate = None

# ─── BLUEPRINT ──────────────────────────────────────────────
intelligence_bp = Blueprint('intelligence', __name__)

# ─── CONSTANTS ──────────────────────────────────────────────
MAX_RECENT_REQUESTS = 500
DEFAULT_MONTHLY_KM = 2000
DEFAULT_YEARLY_KM = 24000
CURRENT_YEAR = datetime.now().year


# ─── HELPER ──────────────────────────────────────────────────
def normalize_score(raw_score, min_val=0, max_val=100):
    """Clamp score between min and max."""
    return max(min_val, min(max_val, raw_score))


# ─── ENDPOINT 1: MARKET TRENDS ──────────────────────────────
@intelligence_bp.route('/market-trends', methods=['GET'])
@require_auth
def market_trends(user):
    """Real market trends based on historical service_requests data."""
    supabase = get_supabase()
    try:
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
            result = item.get('result', {})
            value = result.get('market_value', item.get('amount', 0))
            if value:
                make_data[make]['total_value'] += value
                make_data[make]['values'].append(value)
            year = item.get('year')
            if year:
                make_data[make]['years'].append(year)

        # Compute trends
        trends = {}
        avg_values = {}
        for make, data in make_data.items():
            if data['values']:
                avg = data['total_value'] / data['count']
                avg_values[make] = round(avg, 2)
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


# ─── ENDPOINT 2: VIN DECODE ─────────────────────────────────
@intelligence_bp.route('/vin-decode', methods=['POST'])
@require_auth
def vin_decode(user):
    """VIN Decoder (placeholder)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    vin = data.get('vin', '').strip().upper()
    if not vin or len(vin) < 11:
        return jsonify({'error': 'Invalid VIN (minimum 11 characters)'}), 400

    # Mock response
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


# ─── ENDPOINT 3: VEHICLE INTELLIGENCE ───────────────────────
@intelligence_bp.route('/vehicle-intelligence', methods=['POST'])
@require_auth
def vehicle_intelligence(user):
    """Compute comprehensive vehicle intelligence score."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    # Input validation
    try:
        make = data.get('make', '').strip()
        model = data.get('model', '').strip()
        year = int(data.get('year', 0))
        mileage = int(data.get('mileage', 0))
        condition = data.get('condition', 'good').lower()
        purpose = data.get('purpose', 'general')
        vehicle_type = data.get('vehicle_type', 'sedan')
        usage = data.get('usage', 'personal')
        region = data.get('region', 'nairobi')
        road_condition = data.get('road_condition', 'good')
        monthly_km = int(data.get('monthly_km', DEFAULT_MONTHLY_KM))
        yearly_km = int(data.get('yearly_km', DEFAULT_YEARLY_KM))
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid numeric input: {str(e)}'}), 400

    if not make or not model or year < 1950 or mileage < 0:
        return jsonify({'error': 'Missing or invalid vehicle parameters'}), 400

    # ─── Get valuation ──────────────────────────────────────────
    valuation_result = None
    market_value = 0
    confidence_score = 70

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
            confidence_score = valuation_result.get('confidence_score', 70)
        except Exception as e:
            logger.error(f"Valuation engine failed: {e}")
            market_value = 0

    # ─── Get mileage running cost ──────────────────────────────
    mileage_result = None
    cost_per_km = 0
    monthly_cost = 0
    yearly_cost = 0

    if calculate_mileage_rate:
        try:
            mileage_result = calculate_mileage_rate(
                vehicle_type=vehicle_type,
                usage=usage,
                region=region,
                road_condition=road_condition,
                purpose="vehicle_running_cost_analysis",
                monthly_km=monthly_km,
                yearly_km=yearly_km
            )
            cost_per_km = mileage_result.get('cost_per_km', 0)
            monthly_cost = mileage_result.get('cost_per_month', 0)
            yearly_cost = mileage_result.get('cost_per_year', 0)
        except Exception as e:
            logger.error(f"Mileage rate engine failed: {e}")
            cost_per_km = 0

    # ─── Compute intelligence scores ──────────────────────────
    heat_score = 50
    if market_value > 0:
        heat_score = 50 + (math.log(max(market_value / 100000, 1)) * 2)
        heat_score = normalize_score(heat_score, 5, 95)

    risk_score = 50
    if year > 0:
        age = CURRENT_YEAR - year
        if age > 10:
            risk_score += 20
        elif age > 5:
            risk_score += 10
        else:
            risk_score -= 10

    if mileage > 150000:
        risk_score += 15
    elif mileage > 80000:
        risk_score += 5

    if condition == 'poor':
        risk_score += 15
    elif condition == 'fair':
        risk_score += 5
    elif condition == 'excellent':
        risk_score -= 10

    risk_score = normalize_score(risk_score, 5, 95)

    if heat_score > 70 and risk_score < 30:
        recommendation = "Strong Buy"
    elif heat_score > 60 and risk_score < 40:
        recommendation = "Buy"
    elif heat_score > 40 and risk_score < 60:
        recommendation = "Hold"
    elif heat_score < 30 and risk_score > 70:
        recommendation = "Sell"
    else:
        recommendation = "Evaluate"

    result = {
        'market_value': market_value,
        'running_costs': {
            'cost_per_km': round(cost_per_km, 2),
            'monthly_cost': monthly_cost,
            'yearly_cost': yearly_cost,
            'monthly_km': monthly_km,
            'yearly_km': yearly_km
        },
        'intelligence': {
            'heat_score': round(heat_score, 1),
            'risk_score': round(risk_score, 1),
            'confidence_score': round(confidence_score, 1),
            'recommendation': recommendation
        },
        'inputs': {
            'make': make,
            'model': model,
            'year': year,
            'mileage': mileage,
            'condition': condition,
            'vehicle_type': vehicle_type,
            'usage': usage,
            'region': region
        }
    }

    return jsonify(result), 200


# ─── ENDPOINT 4: QUICK MARKET CHECK ──────────────────────────
@intelligence_bp.route('/quick-check', methods=['POST'])
@require_auth
def quick_market_check(user):
    """Quick market check for a vehicle."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    try:
        make = data.get('make', '').strip()
        model = data.get('model', '').strip()
        year = int(data.get('year', 0))
        mileage = int(data.get('mileage', 0))
        condition = data.get('condition', 'good').lower()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid numeric input for year or mileage'}), 400

    if not make or not model or year < 1950:
        return jsonify({'error': 'Missing or invalid vehicle parameters'}), 400

    market_value = 0
    if calculate_value:
        try:
            valuation_result = calculate_value(
                make=make,
                model=model,
                year=year,
                odometer=mileage,
                condition=condition
            )
            market_value = valuation_result.get('market_value', 0)
        except Exception as e:
            logger.error(f"Quick check valuation failed: {e}")

    return jsonify({
        'market_value': market_value,
        'make': make,
        'model': model,
        'year': year
    }), 200


# ─── ENDPOINT 5: INTELLIGENCE DASHBOARD ──────────────────────
@intelligence_bp.route('/dashboard', methods=['GET'])
@require_auth
def intelligence_dashboard(user):
    """Admin dashboard: market summaries, top trends."""
    supabase = get_supabase()
    try:
        # Top 5 makes by valuation count
        resp = supabase.table('service_requests')\
            .select('make')\
            .eq('service_type', 'valuation')\
            .execute()

        top_makes = []
        make_counts = {}
        if resp.data:
            for item in resp.data:
                make = item.get('make', 'Unknown')
                make_counts[make] = make_counts.get(make, 0) + 1
            top_makes = sorted(make_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return jsonify({
            'top_makes': [{'make': m, 'count': c} for m, c in top_makes],
            'total_valuations': len(resp.data) if resp.data else 0,
            'message': 'Intelligence dashboard'
        }), 200

    except Exception as e:
        logger.error(f"Dashboard error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': 'Unable to load dashboard'}), 500
