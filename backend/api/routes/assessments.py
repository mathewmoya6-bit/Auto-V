# api/routes/assessment.py
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import uuid
import random

from services.supabase_client import get_supabase
from services.vin_validator import vin_validator
from services.carapi_service import get_carapi_service
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

assessment_bp = Blueprint('assessment', __name__)

# ─── ASSESSMENT ENGINE ──────────────────────────────────────────

def calculate_assessment(assessment_data: dict) -> dict:
    """
    Calculate assessment results based on type and vehicle data.
    Returns comprehensive assessment with recommendations.
    """
    assessment_type = assessment_data.get('assessment_type', 'accident')
    vehicle = assessment_data.get('vehicle', {})
    market_value = vehicle.get('market_value', 2000000)
    
    # Base result structure
    result = {
        'assessment_id': f"ASM-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
        'type': assessment_type,
        'confidence_score': 85,
        'generated_at': datetime.now().isoformat(),
        'inspector': assessment_data.get('inspector', {})
    }
    
    # Assessment type-specific calculations
    if assessment_type == 'accident':
        result = calculate_accident_assessment(assessment_data, vehicle, result)
    elif assessment_type == 'insurance_claim':
        result = calculate_insurance_claim(assessment_data, vehicle, result)
    elif assessment_type == 'repair_cost':
        result = calculate_repair_cost(assessment_data, vehicle, result)
    elif assessment_type == 'total_loss':
        result = calculate_total_loss(assessment_data, vehicle, result)
    elif assessment_type == 'salvage':
        result = calculate_salvage(assessment_data, vehicle, result)
    elif assessment_type == 'theft_recovery':
        result = calculate_theft_recovery(assessment_data, vehicle, result)
    
    return result

def calculate_accident_assessment(data, vehicle, result):
    """Calculate accident assessment results"""
    severity = data.get('damage_severity', 'moderate')
    parts_affected = data.get('parts_affected', [])
    market_value = vehicle.get('market_value', 2000000)
    
    # Estimate repair costs based on severity
    severity_multipliers = {
        'minor': 0.05,
        'moderate': 0.15,
        'major': 0.35,
        'severe': 0.55,
        'catastrophic': 0.85
    }
    
    multiplier = severity_multipliers.get(severity, 0.15)
    repair_cost = market_value * multiplier
    
    # Add parts cost
    parts_cost = len(parts_affected) * 15000 if parts_affected else 0
    labour_hours = len(parts_affected) * 4 if parts_affected else 0
    labour_cost = labour_hours * 1500
    
    total_repair = repair_cost + parts_cost + labour_cost
    
    # Determine if total loss
    total_loss = total_repair > (market_value * 0.75)
    
    result.update({
        'repair_estimate': {
            'parts_cost': round(parts_cost),
            'labour_cost': round(labour_cost),
            'total_cost': round(total_repair)
        },
        'total_loss': total_loss,
        'loss_ratio': round(total_repair / market_value, 2),
        'recommendation': 'Total Loss' if total_loss else 'Repairable'
    })
    
    return result

def calculate_insurance_claim(data, vehicle, result):
    """Calculate insurance claim assessment"""
    severity = data.get('damage_severity', 'moderate')
    market_value = vehicle.get('market_value', 2000000)
    policy_excess = data.get('policy_excess', 0)
    
    severity_factors = {
        'minor': 0.08,
        'moderate': 0.20,
        'major': 0.40,
        'severe': 0.60
    }
    
    factor = severity_factors.get(severity, 0.20)
    claim_amount = market_value * factor
    
    # Apply policy excess
    payout = max(0, claim_amount - policy_excess)
    
    result.update({
        'repair_estimate': {
            'parts_cost': round(claim_amount * 0.6),
            'labour_cost': round(claim_amount * 0.4),
            'total_cost': round(claim_amount)
        },
        'policy_excess': policy_excess,
        'estimated_payout': round(payout),
        'claim_valid': payout > 0,
        'recommendation': 'Claim Approved' if payout > 0 else 'Claim Denied'
    })
    
    return result

def calculate_repair_cost(data, vehicle, result):
    """Calculate repair cost estimate"""
    severity = data.get('damage_severity', 'moderate')
    parts_affected = data.get('parts_affected', [])
    labour_hours = data.get('labour_hours', 0)
    market_value = vehicle.get('market_value', 2000000)
    
    severity_factors = {
        'minor': 0.05,
        'moderate': 0.15,
        'major': 0.35,
        'severe': 0.55
    }
    
    factor = severity_factors.get(severity, 0.15)
    parts_cost = market_value * factor
    
    if not labour_hours:
        labour_hours = len(parts_affected) * 3 if parts_affected else 0
    
    labour_cost = labour_hours * 1500
    total_cost = parts_cost + labour_cost
    
    result.update({
        'repair_estimate': {
            'parts_cost': round(parts_cost),
            'labour_cost': round(labour_cost),
            'total_cost': round(total_cost),
            'labour_hours': labour_hours
        },
        'recommendation': 'Repair Estimate Complete'
    })
    
    return result

def calculate_total_loss(data, vehicle, result):
    """Calculate total loss determination"""
    repair_estimate = data.get('repair_estimate', 0)
    market_value = vehicle.get('market_value', 2000000)
    salvage_value = data.get('salvage_value', market_value * 0.2)
    
    is_total_loss = repair_estimate > (market_value * 0.75)
    loss_ratio = repair_estimate / market_value if market_value > 0 else 1
    
    result.update({
        'repair_estimate': repair_estimate,
        'salvage_value': salvage_value,
        'total_loss': is_total_loss,
        'loss_ratio': round(loss_ratio, 2),
        'estimated_payout': round(market_value - salvage_value if is_total_loss else repair_estimate),
        'recommendation': 'Total Loss - Payout' if is_total_loss else 'Repair and Continue'
    })
    
    return result

def calculate_salvage(data, vehicle, result):
    """Calculate salvage value assessment"""
    severity = data.get('damage_severity', 'moderate')
    market_value = vehicle.get('market_value', 2000000)
    
    salvage_factors = {
        'minor': 0.70,
        'moderate': 0.50,
        'major': 0.30,
        'severe': 0.15,
        'catastrophic': 0.05
    }
    
    factor = salvage_factors.get(severity, 0.50)
    salvage_value = market_value * factor
    
    result.update({
        'salvage_value': round(salvage_value),
        'valuation_recommendation': f'Salvage Value: {round(salvage_value / 1000)}K',
        'recommendation': 'Salvage Valuation Complete'
    })
    
    return result

def calculate_theft_recovery(data, vehicle, result):
    """Calculate theft recovery assessment"""
    condition = data.get('condition', 'fair')
    market_value = vehicle.get('market_value', 2000000)
    
    condition_factors = {
        'excellent': 0.85,
        'good': 0.70,
        'fair': 0.55,
        'poor': 0.40,
        'damaged': 0.25
    }
    
    factor = condition_factors.get(condition, 0.55)
    recovered_value = market_value * factor
    
    result.update({
        'recovered_value': round(recovered_value),
        'valuation_recommendation': f'Recovered Value: {round(recovered_value / 1000)}K',
        'recommendation': 'Theft Recovery Assessment Complete'
    })
    
    return result

# ─── ROUTES ──────────────────────────────────────────────────────

@assessment_bp.route('/create', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def create_assessment():
    """Create a new vehicle assessment"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        if not data.get('assessment_type'):
            return jsonify({
                'success': False,
                'error': 'assessment_type is required'
            }), 400
        
        if not data.get('vehicle') or not data.get('vehicle', {}).get('make'):
            return jsonify({
                'success': False,
                'error': 'Vehicle make is required'
            }), 400
        
        # Calculate assessment
        result = calculate_assessment(data)
        
        # Add user_id
        result['user_id'] = request.user_id
        
        # Save to Supabase
        try:
            supabase = get_supabase()
            supabase.save_assessment({
                'assessment_id': result['assessment_id'],
                'user_id': request.user_id,
                'assessment_type': data['assessment_type'],
                'vehicle_data': data.get('vehicle', {}),
                'inspector': data.get('inspector', {}),
                'result': result,
                'created_at': datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Failed to save assessment: {str(e)}")
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Assessment completed successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Assessment error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessment_bp.route('/<assessment_id>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_assessment(assessment_id):
    """Get assessment by ID"""
    try:
        supabase = get_supabase()
        result = supabase.get_assessment(assessment_id)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Assessment not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Get assessment error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessment_bp.route('/vehicle/<vin>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_assessments_by_vin(vin):
    """Get all assessments for a vehicle"""
    try:
        vin = vin.upper().strip()
        
        supabase = get_supabase()
        results = supabase.get_assessments_by_vin(vin)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        }), 200
        
    except Exception as e:
        logger.error(f"Get assessments by VIN error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@assessment_bp.route('/stats', methods=['GET'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_assessment_stats():
    """Get assessment statistics"""
    try:
        supabase = get_supabase()
        stats = supabase.get_assessment_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Get assessment stats error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
