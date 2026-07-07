# app/core/supabase.py
# =============================================================================
# AUTO-V API - Supabase Client
# =============================================================================

import os
from supabase import create_client, Client
from typing import Optional, Dict, Any

# ─── Supabase Configuration ──────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Create Supabase client
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    print("✅ Supabase client initialized")
else:
    print("⚠️  Supabase credentials not configured")


def get_supabase() -> Optional[Client]:
    """Get Supabase client instance"""
    return supabase


def get_admin_client() -> Optional[Client]:
    """Get Supabase admin client with service role key"""
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return None


def is_supabase_configured() -> bool:
    """Check if Supabase is configured"""
    return supabase is not None


# ─── Supabase Auth Functions ────────────────────────────────────────

async def sign_up_user(
    email: str,
    password: str,
    user_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Register a new user with Supabase
    
    Args:
        email: User email
        password: User password
        user_metadata: Additional user data (full_name, phone, etc.)
    
    Returns:
        Dict with user data and session
    """
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    try:
        # Prepare user metadata
        metadata = user_metadata or {}
        
        # Sign up with Supabase
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": metadata.get("full_name", ""),
                    "phone": metadata.get("phone", ""),
                    "company_name": metadata.get("company_name", ""),
                    "role": "user"
                }
            }
        })
        
        if response.user:
            return {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": response.user.user_metadata.get("full_name"),
                    "phone": response.user.user_metadata.get("phone"),
                    "role": response.user.user_metadata.get("role", "user"),
                    "created_at": response.user.created_at,
                    "is_verified": response.user.email_confirmed_at is not None
                },
                "session": response.session
            }
        else:
            return {
                "success": False,
                "error": "Registration failed"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def sign_in_user(email: str, password: str) -> Dict[str, Any]:
    """
    Sign in a user with Supabase
    
    Args:
        email: User email
        password: User password
    
    Returns:
        Dict with user data and session
    """
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            return {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": response.user.user_metadata.get("full_name"),
                    "phone": response.user.user_metadata.get("phone"),
                    "role": response.user.user_metadata.get("role", "user"),
                    "created_at": response.user.created_at,
                    "is_verified": response.user.email_confirmed_at is not None
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": response.session.expires_at
                }
            }
        else:
            return {
                "success": False,
                "error": "Invalid credentials"
            }
            
    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            return {
                "success": False,
                "error": "Invalid email or password"
            }
        elif "Email not confirmed" in error_msg:
            return {
                "success": False,
                "error": "Please verify your email before logging in"
            }
        return {
            "success": False,
            "error": error_msg
        }


async def sign_out_user(access_token: str) -> Dict[str, Any]:
    """Sign out a user"""
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    try:
        supabase.auth.sign_out()
        return {"success": True, "message": "Signed out successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_user_by_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Get user from access token"""
    if not supabase:
        return None
    
    try:
        # Set the session with the token
        supabase.auth.set_session(access_token, "")
        user = supabase.auth.get_user()
        
        if user:
            return {
                "id": user.user.id,
                "email": user.user.email,
                "full_name": user.user.user_metadata.get("full_name"),
                "phone": user.user.user_metadata.get("phone"),
                "role": user.user.user_metadata.get("role", "user"),
                "created_at": user.user.created_at,
                "is_verified": user.user.email_confirmed_at is not None
            }
        return None
        
    except Exception as e:
        print(f"Error getting user from token: {e}")
        return None


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token"""
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    try:
        response = supabase.auth.refresh_session(refresh_token)
        return {
            "success": True,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "expires_at": response.session.expires_at
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def reset_password(email: str) -> Dict[str, Any]:
    """Send password reset email"""
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    try:
        supabase.auth.reset_password_for_email(email)
        return {
            "success": True,
            "message": "Password reset email sent"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def update_user_metadata(user_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Update user metadata"""
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    try:
        response = supabase.auth.update_user({
            "data": metadata
        })
        return {
            "success": True,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "metadata": response.user.user_metadata
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
