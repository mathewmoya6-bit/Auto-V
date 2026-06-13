from fastapi import HTTPException
from auth_guard import get_user_role

def require_role(user_id, allowed_roles):

    role = get_user_role(user_id)

    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    return True
