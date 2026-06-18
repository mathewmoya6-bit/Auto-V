from functools import wraps
from flask import request, jsonify
from services.supabase_client import get_supabase
import logging

logger = logging.getLogger(__name__)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            logger.warning("Missing Authorization header")
            return jsonify({'error': 'Missing token'}), 401

        try:
            # Token format: "Bearer <token>"
            token_parts = token.split()
            if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
                raise ValueError("Invalid token format")
            jwt = token_parts[1]

            supabase = get_supabase()
            # Verify token with Supabase
            user_response = supabase.auth.get_user(jwt)
            user = user_response.user
            if not user:
                raise Exception("User not found")
            return f(user, *args, **kwargs)
        except Exception as e:
            logger.warning(f"Authentication failed: {str(e)}")
            return jsonify({'error': 'Invalid token'}), 401
    return decorated
