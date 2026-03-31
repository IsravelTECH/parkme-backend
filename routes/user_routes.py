from fastapi import APIRouter, HTTPException
from models.user_model import SignupRequest
from models.user_model import LoginRequest  
from models.user_model import User
from database import database
from passlib.context import CryptContext
from auth import create_access_token
from auth import verify_token, require_role
from fastapi import Depends
from auth import require_role
from fastapi import Response
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"

def create_token(user_id: str):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=5)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return token

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/signup")
async def signup(user: SignupRequest):

    # Check if email already exists
    existing_user = await database.users.find_one({"email": user.email})

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = pwd_context.hash(user.password)

    new_user = {
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "password": hashed_password,
        "role": "seeker"  # default role
    }

    result = await database.users.insert_one(new_user)

    # ✅ CREATE TOKEN (IMPORTANT)
    token = create_token(str(result.inserted_id))

    # ✅ RETURN SAME AS LOGIN
    return {
        "message": "User created successfully",
        "token": token,
        "name": user.name,
        "role": user.role
    }

@router.post("/login")
async def login(data: LoginRequest):

    user = await database.users.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if not pwd_context.verify(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid password")

    token = create_token(str(user["_id"]))

    return {
        "message": "Login successful",
        "token": token,
        "name": user["name"],
        "role": user["role"]
    }


@router.delete("/delete-all")
async def delete_all():
    await database.users.delete_many({})
    return {"message": "All users deleted"}

@router.get("/protected")
async def protected_route(user=Depends(verify_token)):
    return {
        "message": "You are authorized",
        "user_data": user
    }

