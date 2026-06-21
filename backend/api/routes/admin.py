# api/routes/admin.py - Admin Routes
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from services.supabase_client import get_supabase
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

# ─── SYSTEM STATUS ─────────────────────────────────────────────

@admin_bp.route('/status', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def system_status():
    """Get system status"""
    try:
        supabase = get_supabase()
        health = supabase.check_health()
        
        return jsonify({
            'success': True,
            'data': {
                'status': 'operational' if health.get('connected') else 'degraded',
                'timestamp': datetime.now().isoformat(),
                'services': {
                    'supabase': health,
                    'api': 'operational'
                }
            }
        }), 200
    except Exception as e:
        logger.error(f"System status error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/stats', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def system_stats():
    """Get system statistics"""
    try:
        supabase = get_supabase()
        stats = supabase.get_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"System stats error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── USERS ──────────────────────────────────────────────────────

@admin_bp.route('/users', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def list_users():
    """List all users"""
    try:
        supabase = get_supabase()
        users = supabase.list_users()
        
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        }), 200
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/users/<user_id>', methods=['GET'])
@rate_limit(limit=30, per=60)
@require_auth
@log_request
def get_user(user_id):
    """Get user by ID"""
    try:
        supabase = get_supabase()
        user = supabase.get_user(user_id)
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'data': user
        }), 200
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/users/<user_id>/status', methods=['PUT'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def update_user_status(user_id):
    """Update user status"""
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'status is required'}), 400
        
        supabase = get_supabase()
        result = supabase.update_user_status(user_id, data['status'])
        
        if not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error')}), 500
        
        return jsonify({
            'success': True,
            'data': result.get('data'),
            'message': 'User status updated'
        }), 200
    except Exception as e:
        logger.error(f"Update user status error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── SYSTEM CONFIG ─────────────────────────────────────────────

@admin_bp.route('/config', methods=['GET'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_config():
    """Get system configuration"""
    try:
        supabase = get_supabase()
        config = supabase.get_system_config()
        
        return jsonify({
            'success': True,
            'data': config
        }), 200
    except Exception as e:
        logger.error(f"Get config error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/config', methods=['PUT'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def update_config():
    """Update system configuration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        supabase = get_supabase()
        result = supabase.update_system_config(data)
        
        if not result.get('success'):
            return jsonify({'success': False, 'error': result.get('error')}), 500
        
        return jsonify({
            'success': True,
            'data': result.get('data'),
            'message': 'Configuration updated'
        }), 200
    except Exception as e:
        logger.error(f"Update config error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── LOGS ──────────────────────────────────────────────────────

@admin_bp.route('/logs', methods=['GET'])
@rate_limit(limit=20, per=60)
@require_auth
@log_request
def get_logs():
    """Get system logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        level = request.args.get('level', 'INFO')
        
        # Read logs from file
        import os
        log_file = os.getenv('LOG_FILE', 'auto-v.log')
        
        if not os.path.exists(log_file):
            return jsonify({
                'success': True,
                'data': [],
                'message': 'No log file found'
            }), 200
        
        with open(log_file, 'r') as f:
            lines = f.readlines()[-limit:]
        
        return jsonify({
            'success': True,
            'data': lines,
            'count': len(lines)
        }), 200
    except Exception as e:
        logger.error(f"Get logs error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── CACHE ──────────────────────────────────────────────────────

@admin_bp.route('/cache/clear', methods=['POST'])
@rate_limit(limit=10, per=60)
@require_auth
@log_request
def clear_cache():
    """Clear system cache"""
    try:
        supabase = get_supabase()
        supabase.clear_cache()
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        }), 200
    except Exception as e:
        logger.error(f"Clear cache error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
