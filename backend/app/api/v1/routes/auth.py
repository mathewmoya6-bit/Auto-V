# app/api/v1/routes/auth.py
#
# NOTE ON SCOPE: actual login/signup/password-reset already happens
# client-side against Supabase Auth (supabase.js: signInWithPassword,
# signOut, etc.) — this backend never sees a raw password. So this
# router doesn't re-implement login; it just exposes what a backend
# typically needs once the frontend already holds a Supabase session
# token: confirming that token is valid, and returning/creating the
# matching profile. If you actually want backend-owned auth instead
# (issuing its own JWTs, checking password_hash directly), say so —
# that's a different router entirely.

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import UserProfile

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me")
async def get_me(current_user: UserProfile = Depends(get_current_user)):
    """Return the profile for whoever's Supabase access_token was sent
    in the Authorization header. Confirms the token is valid and gives
    the frontend a single place to fetch role/profile info from this
    backend rather than querying Supabase directly, if desired."""
    return current_user.to_dict()


@router.post("/verify")
async def verify_token(current_user: UserProfile = Depends(get_current_user)):
    """Lightweight endpoint the frontend can call just to check whether
    a stored session token is still valid (e.g. on app load)."""
    return {"valid": True, "user_id": str(current_user.id), "role": current_user.role}
