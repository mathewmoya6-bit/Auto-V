# app/services/supabase_service.py
from typing import Optional, Dict, Any
from app.core.database import get_supabase

async def sign_up_user(email: str, password: str, metadata: Optional[Dict] = None) -> Dict:
    supabase = get_supabase()
    if not supabase:
        return {"success": False, "error": "Supabase not configured"}
    
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": metadata or {}}
        })
        
        if response.user:
            return {
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": response.user.user_metadata.get("full_name"),
                    "role": response.user.user_metadata.get("role", "user"),
                },
                "session": response.session
            }
        return {"success": False, "error": "Registration failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def sign_in_user(email: str, password: str) -> Dict:
    supabase = get_supabase()
    if not supabase:
        return {"success": False, "error": "Supabase not configured"}
    
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
                    "role": response.user.user_metadata.get("role", "user"),
                },
                "session": {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                }
            }
        return {"success": False, "error": "Invalid credentials"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_user_by_token(token: str) -> Optional[Dict]:
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        supabase.auth.set_session(token, "")
        user = supabase.auth.get_user()
        if user:
            return {
                "id": user.user.id,
                "email": user.user.email,
                "full_name": user.user.user_metadata.get("full_name"),
                "role": user.user.user_metadata.get("role", "user"),
            }
        return None
    except Exception:
        return None
