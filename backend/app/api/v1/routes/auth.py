# app/api/v1/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.services.supabase_service import sign_up_user, sign_in_user, get_user_by_token
from app.core.security import create_access_token

router = APIRouter(tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    phone: Optional[str] = None
    company_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: dict


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    user = await get_user_by_token(parts[1])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest):
    result = await sign_up_user(
        email=payload.email,
        password=payload.password,
        metadata={
            "full_name": payload.full_name,
            "phone": payload.phone,
            "company_name": payload.company_name,
            "role": "user"
        }
    )
    
    if not result["success"]:
        if "already registered" in result.get("error", "").lower():
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=400, detail=result.get("error", "Registration failed"))
    
    return {"message": "User registered successfully. Please verify your email.", "user": result["user"]}


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    result = await sign_in_user(email=payload.email, password=payload.password)
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return TokenResponse(
        access_token=result["session"]["access_token"],
        user=result["user"]
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.get("/ping")
async def ping():
    return {"status": "ok", "message": "Auth router is working"}
