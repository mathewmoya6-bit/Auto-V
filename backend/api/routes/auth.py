# api/routes/auth.py – Flask Blueprint (PRODUCTION READY)

import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from services.supabase_client import get_supabase
from api.auth_middleware import require_auth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

# ─── Rate Limiter ──────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use Redis in production
)

# ============================================================
# LOGIN
# ============================================================
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")  # Prevent brute force
def login():
    """
    Authenticate user with email and password.
    
    Request body:
        {
            "email": "user@example.com",
            "password": "password123"
        }
    
    Response:
        {
            "access_token": "jwt_token",
            "refresh_token": "refresh_token",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": {
                "id": "uuid",
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "user",
                "phone": "0712345678"
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Missing request body'}), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        supabase = get_supabase()
        
        # Attempt login
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
        except Exception as e:
            logger.warning(f"Login failed for {email}: {str(e)}")
            return jsonify({'error': 'Invalid email or password'}), 401
        
        session = response.session
        if not session or not response.user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Get user profile
        profile_response = supabase.table('user_profiles')\
            .select('*')\
            .eq('id', response.user.id)\
            .execute()
        
        user_data = {
            'id': response.user.id,
            'email': response.user.email,
            'user_metadata': response.user.user_metadata or {},
        }
        
        if profile_response.data:
            profile = profile_response.data[0]
            user_data.update({
                'full_name': profile.get('full_name'),
                'phone': profile.get('phone'),
                'role': profile.get('role', 'user'),
                'first_login': profile.get('first_login', True),
                'has_vehicle': profile.get('has_vehicle', False),
                'created_at': profile.get('created_at'),
            })
            
            # Update login count
            supabase.table('user_profiles')\
                .update({
                    'login_count': profile.get('login_count', 0) + 1,
                    'last_login': datetime.now().isoformat()
                })\
                .eq('id', response.user.id)\
                .execute()
        else:
            # Create profile if it doesn't exist
            profile_data = {
                "id": response.user.id,
                "email": email,
                "full_name": response.user.user_metadata.get('full_name', email.split('@')[0]),
                "role": "user",
                "first_login": True,
                "login_count": 1,
                "created_at": datetime.now().isoformat()
            }
            supabase.table('user_profiles').insert(profile_data).execute()
            user_data.update({
                'full_name': profile_data['full_name'],
                'role': 'user',
                'first_login': True,
                'has_vehicle': False,
            })
        
        # Log successful login
        logger.info(f"✅ User logged in: {email}")
        
        return jsonify({
            'access_token': session.access_token,
            'refresh_token': session.refresh_token,
            'expires_in': session.expires_in,
            'token_type': 'bearer',
            'user': user_data
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================
# SIGNUP
# ============================================================
@auth_bp.route('/signup', methods=['POST'])
@limiter.limit("5 per minute")  # Prevent spam
def signup():
    """
    Register a new user.
    
    Request body:
        {
            "email": "user@example.com",
            "password": "password123",
            "full_name": "John Doe",
            "phone": "0712345678"
        }
    
    Response:
        Same as login (auto-login after signup)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Missing request body'}), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        supabase = get_supabase()
        
        # Check if user already exists
        existing = supabase.table('user_profiles')\
            .select('email')\
            .eq('email', email)\
            .execute()
        
        if existing.data:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Sign up user
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name or email.split('@')[0],
                        "phone": phone,
                    }
                }
            })
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            if "already registered" in str(e).lower():
                return jsonify({'error': 'User already registered'}), 409
            return jsonify({'error': 'Signup failed'}), 400
        
        if not response.user:
            return jsonify({'error': 'Signup failed'}), 400
        
        # Create user profile
        profile_data = {
            "id": response.user.id,
            "email": email,
            "full_name": full_name or email.split('@')[0],
            "phone": phone,
            "role": "user",
            "first_login": True,
            "has_vehicle": False,
            "login_count": 1,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table('user_profiles').insert(profile_data).execute()
        
        # Auto-login
        try:
            login_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if login_response.session:
                logger.info(f"✅ User signed up and logged in: {email}")
                return jsonify({
                    'access_token': login_response.session.access_token,
                    'refresh_token': login_response.session.refresh_token,
                    'expires_in': login_response.session.expires_in,
                    'token_type': 'bearer',
                    'user': {
                        'id': response.user.id,
                        'email': email,
                        'full_name': profile_data['full_name'],
                        'phone': phone,
                        'role': 'user',
                        'first_login': True,
                        'has_vehicle': False,
                    }
                }), 201
        except:
            # Auto-login failed, but account was created
            return jsonify({
                'message': 'Account created. Please log in.',
                'user': profile_data
            }), 201
        
        return jsonify({
            'message': 'Account created. Please log in.',
            'user': profile_data
        }), 201
        
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================
# REFRESH TOKEN
# ============================================================
@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """
    Refresh the access token using a valid refresh token.
    
    Request body:
        {
            "refresh_token": "refresh_token_string"
        }
    """
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 400
        
        supabase = get_supabase()
        response = supabase.auth.refresh_session(refresh_token)
        
        if not response.session:
            return jsonify({'error': 'Invalid refresh token'}), 401
        
        user_data = {
            'id': response.user.id,
            'email': response.user.email,
        }
        
        # Get user profile
        profile_response = supabase.table('user_profiles')\
            .select('*')\
            .eq('id', response.user.id)\
            .execute()
        
        if profile_response.data:
            user_data.update(profile_response.data[0])
        
        return jsonify({
            'access_token': response.session.access_token,
            'refresh_token': response.session.refresh_token,
            'expires_in': response.session.expires_in,
            'token_type': 'bearer',
            'user': user_data
        }), 200
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Invalid refresh token'}), 401


# ============================================================
# GET CURRENT USER
# ============================================================
@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_me(user):
    """
    Get the current authenticated user's profile.
    """
    try:
        supabase = get_supabase()
        
        profile_response = supabase.table('user_profiles')\
            .select('*')\
            .eq('id', user.id)\
            .execute()
        
        user_data = {
            'id': user.id,
            'email': user.email,
        }
        
        if profile_response.data:
            user_data.update(profile_response.data[0])
        
        # Add user_metadata
        if user.user_metadata:
            user_data['user_metadata'] = user.user_metadata
        
        return jsonify(user_data), 200
        
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================
# LOGOUT
# ============================================================
@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout(user):
    """
    Logout the current user.
    """
    try:
        supabase = get_supabase()
        # Supabase sign_out is client-side; we just log the event
        logger.info(f"User logged out: {user.email}")
        return jsonify({'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500


# ============================================================
# CHANGE PASSWORD
# ============================================================
@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password(user):
    """
    Change the user's password.
    
    Request body:
        {
            "current_password": "old_password",
            "new_password": "new_password"
        }
    """
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new password required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400
        
        supabase = get_supabase()
        
        # Verify current password by attempting login
        try:
            supabase.auth.sign_in_with_password({
                "email": user.email,
                "password": current_password
            })
        except:
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        supabase.auth.update_user({
            "password": new_password
        })
        
        logger.info(f"Password updated for: {user.email}")
        return jsonify({'message': 'Password updated successfully'}), 200
        
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return jsonify({'error': 'Failed to update password'}), 500


# ============================================================
# FORGOT PASSWORD
# ============================================================
@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("3 per hour")
def forgot_password():
    """
    Send password reset email.
    
    Request body:
        {
            "email": "user@example.com"
        }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        supabase = get_supabase()
        
        # Send reset email
        supabase.auth.reset_password_for_email(email)
        
        logger.info(f"Password reset email sent to: {email}")
        return jsonify({'message': 'Password reset email sent'}), 200
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'error': 'Failed to send reset email'}), 500


# ============================================================
# UPDATE PROFILE
# ============================================================
@auth_bp.route('/update-profile', methods=['PUT'])
@require_auth
def update_profile(user):
    """
    Update user profile.
    
    Request body:
        {
            "full_name": "John Doe",
            "phone": "0712345678"
        }
    """
    try:
        data = request.get_json()
        supabase = get_supabase()
        
        update_data = {}
        if 'full_name' in data:
            update_data['full_name'] = data['full_name'].strip()
        if 'phone' in data:
            update_data['phone'] = data['phone'].strip()
        
        if not update_data:
            return jsonify({'error': 'No fields to update'}), 400
        
        update_data['updated_at'] = datetime.now().isoformat()
        
        response = supabase.table('user_profiles')\
            .update(update_data)\
            .eq('id', user.id)\
            .execute()
        
        if not response.data:
            return jsonify({'error': 'Profile update failed'}), 500
        
        logger.info(f"Profile updated for: {user.email}")
        return jsonify({
            'message': 'Profile updated successfully',
            'user': response.data[0]
        }), 200
        
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': 'Failed to update profile'}), 500
