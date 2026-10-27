import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from bson import ObjectId
from dotenv import load_dotenv
from database import database

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "parkme_secure_jwt_secret_key_2026_default_fallback")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()

def create_access_token(user_id: str, role: str = "seeker", expires_hours: int = ACCESS_TOKEN_EXPIRE_HOURS) -> str:
    """Generate a signed JWT token containing user id, role, and expiration."""
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Decodes and validates a Bearer JWT token, returning the payload dictionary."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifies the token and fetches the full user document from the database."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await database.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_role(required_role: str):
    """Dependency that enforces a specific user role."""
    async def role_checker(user=Depends(get_current_user)):
        if user.get("role") != required_role:
            raise HTTPException(status_code=403, detail=f"Access denied: {required_role} role required")
        return user
    return role_checker

def require_owner(user=Depends(get_current_user)):
    """Dependency that enforces the owner or admin role."""
    role = str(user.get("role", "")).lower()
    if role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied: owner or admin role required")
    return user