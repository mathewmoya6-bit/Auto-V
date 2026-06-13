from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationHeader
from typing import List

security = HTTPBearer()

async def require_role(required_roles: List[str], token: str = Depends(security)):
    """
    Dependency that validates user role from JWT token
    """
    # Extract user_id and role from token
    # This depends on your auth implementation (JWT, session, etc.)
    user_id = decode_token_get_user_id(token)  # Implement this
    
    # Get user role from database
    user_role = await get_user_role(user_id)  # Implement this
    
    if user_role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {user_role} not authorized. Required: {required_roles}"
        )
    
    return {"user_id": user_id, "role": user_role}
