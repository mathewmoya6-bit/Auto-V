from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta
import jwt

from services.supabase_client import supabase
from config import settings

router = APIRouter()

# ============================================
# PYDANTIC MODELS
# ============================================
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ============================================
# HELPER FUNCTIONS
# ============================================
def generate_token(user_id: str, email: str, role: str = "user"):
    expiry = datetime.now() + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expiry
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

# ============================================
# ROUTES
# ============================================
@router.post("/register")
async def register(user: UserRegister):
    try:
        existing = supabase.table("user_profiles")\\
            .select("email")\\
            .eq("email", user.email)\\
            .execute()
        
        if existing.data:
            raise HTTPException(status_code=400, detail="User already exists")
        
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {
                    "full_name": user.full_name or user.email.split('@')[0],
                    "phone": user.phone or ""
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
        
        profile = {
            "id": auth_response.user.id,
            "email": user.email,
            "full_name": user.full_name or user.email.split('@')[0],
            "phone": user.phone or "",
            "role": "user",
            "first_login": True,
            "has_vehicle": False,
            "login_count": 0,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("user_profiles").insert(profile).execute()
        
        return {
            "message": "User registered successfully",
            "user_id": auth_response.user.id,
            "email": user.email
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        profile_response = supabase.table("user_profiles")\\
            .select("*")\\
            .eq("id", auth_response.user.id)\\
            .single()\\
            .execute()
        
        if not profile_response.data:
            profile_data = {
                "id": auth_response.user.id,
                "email": user.email,
                "full_name": user.email.split('@')[0],
                "role": "user",
                "first_login": True,
                "has_vehicle": False,
                "login_count": 1,
                "created_at": datetime.now().isoformat()
            }
            supabase.table("user_profiles").insert(profile_data).execute()
            profile = profile_data
        else:
            profile = profile_response.data
            new_count = profile.get("login_count", 0) + 1
            supabase.table("user_profiles")\\
                .update({
                    "login_count": new_count,
                    "last_login": datetime.now().isoformat()
                })\\
                .eq("id", auth_response.user.id)\\
                .execute()
        
        token = generate_token(
            auth_response.user.id,
            user.email,
            profile.get("role", "user")
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": auth_response.user.id,
                "email": user.email,
                "full_name": profile.get("full_name"),
                "phone": profile.get("phone"),
                "role": profile.get("role", "user"),
                "created_at": profile.get("created_at")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
async def logout():
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
