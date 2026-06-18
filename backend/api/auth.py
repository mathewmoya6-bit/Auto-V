# api/auth.py – Flask Blueprint
from flask import Blueprint, request, jsonify
from services.supabase_client import get_supabase
from api.auth_middleware import require_auth
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    try:
        supabase = get_supabase()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        session = response.session
        if not session:
            return jsonify({'error': 'Invalid credentials'}), 401

        return jsonify({
            'access_token': session.access_token,
            'refresh_token': session.refresh_token,
            'user': {
                'id': response.user.id,
                'email': response.user.email
            }
        }), 200
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Authentication failed'}), 401

@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_me(user):
    return jsonify({
        'id': user.id,
        'email': user.email,
        'created_at': user.created_at
    }), 200
