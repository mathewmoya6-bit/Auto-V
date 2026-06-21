# api/routes/auth.py - Authentication Routes
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging
import jwt
import os

from services.supabase_client import get_supabase
from utils.decorators import rate_limit, require_auth, log_request

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# ─── REGISTER ───────────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
@rate_limit(limit=10, per=60)
@log_request
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required = ['email', 'password', 'full_name']
        missing = [f for f in required if not data.get(f)]
        
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing fields: {", ".join(missing)}'
            }), 400
        
        # Register user
        supabase = get_supabase()
        result = supabase.register_user(
            email=data['email'],
            password=data['password'],
            metadata={
                'full_name': data['full_name'],
                'phone': data.get('phone'),
                'company': data.get('company')
            }
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Registration failed')
            }), 400
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': result.get('user_id'),
                'email': data['email'],
                'full_name': data['full_name']
            },
            'message': 'Registration successful. Please verify your email.'
        }), 201
        
    except Exception as e:
        logger.error(f"Register error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── LOGIN ──────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['POST'])
@rate_limit(limit=20, per=60)
@log_request
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        # Login user
        supabase = get_supabase()
        result = supabase.login_user(data['email'], data['password'])
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Invalid credentials')
            }), 401
        
        return jsonify({
            'success': True,
            'data': {
                'access_token': result.get('access_token'),
                'refresh_token': result.get('refresh_token'),
                'user': result.get('user')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── LOGOUT ─────────────────────────────────────────────────────

@auth_bp.route('/logout', methods=['POST'])
@require_auth
@log_request
def logout():
    """Logout user"""
    try:
        supabase = get_supabase()
        supabase.logout_user()
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── ME ─────────────────────────────────────────────────────────

@auth_bp.route('/me', methods=['GET'])
@require_auth
@log_request
def get_current_user():
    """Get current user"""
    try:
        supabase = get_supabase()
        result = supabase.get_current_user()
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Not authenticated')
            }), 401
        
        return jsonify({
            'success': True,
            'data': result.get('user')
        }), 200
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── REFRESH ────────────────────────────────────────────────────

@auth_bp.route('/refresh', methods=['POST'])
@rate_limit(limit=20, per=60)
@log_request
def refresh_token():
    """Refresh access token"""
    try:
        data = request.get_json()
        
        if not data or 'refresh_token' not in data:
            return jsonify({
                'success': False,
                'error': 'refresh_token is required'
            }), 400
        
        supabase = get_supabase()
        result = supabase.refresh_session(data['refresh_token'])
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Invalid refresh token')
            }), 401
        
        return jsonify({
            'success': True,
            'data': {
                'access_token': result.get('access_token')
            }
        }), 200
    except Exception as e:
        logger.error(f"Refresh token error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── RESET PASSWORD ────────────────────────────────────────────

@auth_bp.route('/reset-password', methods=['POST'])
@rate_limit(limit=5, per=60)
@log_request
def reset_password():
    """Request password reset"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({
                'success': False,
                'error': 'email is required'
            }), 400
        
        supabase = get_supabase()
        result = supabase.reset_password(data['email'])
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Password reset failed')
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Password reset email sent'
        }), 200
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── VERIFY ─────────────────────────────────────────────────────

@auth_bp.route('/verify', methods=['POST'])
@rate_limit(limit=10, per=60)
@log_request
def verify_email():
    """Verify email with OTP"""
    try:
        data = request.get_json()
        
        if not data or 'email' not in data or 'otp' not in data:
            return jsonify({
                'success': False,
                'error': 'email and otp are required'
            }), 400
        
        supabase = get_supabase()
        result = supabase.verify_email(data['email'], data['otp'])
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Verification failed')
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully'
        }), 200
    except Exception as e:
        logger.error(f"Verify email error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
