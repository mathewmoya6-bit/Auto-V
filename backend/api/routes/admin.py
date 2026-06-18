# api/routes/admin.py - Admin Routes

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from api.auth_middleware import require_auth

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@require_auth
def dashboard(user):
    """Get admin dashboard data."""
    try:
        # Check if user is admin
        if not user.user_metadata.get('role') == 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        supabase = get_supabase()
        
        # Get stats
        users = supabase.table('users').select('*', count='exact').execute()
        payments = supabase.table('payments').select('*', count='exact').execute()
        valuations = supabase.table('valuations').select('*', count='exact').execute()
        
        return jsonify({
            'total_users': users.count if users else 0,
            'total_payments': payments.count if payments else 0,
            'total_valuations': valuations.count if valuations else 0,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500

@admin_bp.route('/users', methods=['GET'])
@require_auth
def get_users(user):
    """Get all users (admin only)."""
    try:
        if not user.user_metadata.get('role') == 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        supabase = get_supabase()
        response = supabase.table('users')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()
        
        return jsonify(response.data), 200
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@require_auth
def update_user(user, user_id):
    """Update a user (admin only)."""
    try:
        if not user.user_metadata.get('role') == 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        data['updated_at'] = datetime.now().isoformat()
        
        supabase = get_supabase()
        response = supabase.table('users')\
            .update(data)\
            .eq('id', user_id)\
            .execute()
        
        if not response.data:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(response.data[0]), 200
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'error': 'Failed to update user'}), 500

@admin_bp.route('/system/settings', methods=['GET'])
@require_auth
def get_settings(user):
    """Get system settings (admin only)."""
    try:
        if not user.user_metadata.get('role') == 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        supabase = get_supabase()
        response = supabase.table('system_settings')\
            .select('*')\
            .execute()
        
        return jsonify(response.data), 200
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        return jsonify({'error': 'Failed to fetch settings'}), 500

@admin_bp.route('/system/settings', methods=['PUT'])
@require_auth
def update_settings(user):
    """Update system settings (admin only)."""
    try:
        if not user.user_metadata.get('role') == 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        data['updated_at'] = datetime.now().isoformat()
        data['updated_by'] = user.id
        
        supabase = get_supabase()
        
        # Update or insert settings
        for key, value in data.items():
            if key in ['updated_at', 'updated_by']:
                continue
            response = supabase.table('system_settings')\
                .upsert({'key': key, 'value': value, 'updated_at': datetime.now().isoformat()})\
                .execute()
        
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({'error': 'Failed to update settings'}), 500

@admin_bp.route('/payments', methods=['GET'])
@require_auth
def get_all_payments(user):
    """Get all payments (admin only)."""
    try:
        if not user.user_metadata.get('role') == 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        supabase = get_supabase()
        response = supabase.table('payments')\
            .select('*, users(full_name, email)')\
            .order('created_at', desc=True)\
            .execute()
        
        return jsonify(response.data), 200
    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        return jsonify({'error': 'Failed to fetch payments'}), 500
