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
        "password": hashed_password
    }

    await database.users.insert_one(new_user)

    return {"message": "User created successfully"}

@router.post("/login")
async def login(data: LoginRequest):

    user = await database.users.find_one({"email": data.email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not pwd_context.verify(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")

    access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user["role"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
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

@router.get("/owner-dashboard")
async def owner_dashboard(user=Depends(require_role("owner"))):
    
    # 1️⃣ Get all parkings of owner
    owner_parkings = []
    async for parking in database.parkings.find(
        {"owner_id": user["sub"]}
    ):
        owner_parkings.append(parking)

    parking_ids = [str(p["_id"]) for p in owner_parkings]

    # 2️⃣ Get bookings for those parkings
    total_bookings = 0
    active_bookings = 0
    completed_bookings = 0
    total_earnings = 0

    async for booking in database.bookings.find(
        {"parking_id": {"$in": parking_ids}}
    ):
        total_bookings += 1

        if booking.get("status") == "active":
            active_bookings += 1

        if booking.get("status") == "completed":
            completed_bookings += 1

        total_earnings += booking.get("total_price", 0)

    return {
        "total_parkings": len(owner_parkings),
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "completed_bookings": completed_bookings,
        "total_earnings": total_earnings
    }

@router.get("/seeker-dashboard")
async def seeker_dashboard(user=Depends(require_role("seeker"))):
    return {"message": "Welcome Seeker", "user": user}


@router.post("/register") 
async def register(user: User): 
# 🔎 Check if email already exists 
    existing_user = await database.users.find_one({"email": user.email}) 
    if existing_user: 
       raise HTTPException(status_code=400, detail="Email already exists") 
    hashed_password = pwd_context.hash(user.password) 

    user_dict = { "name": user.name, "email": user.email, "password": hashed_password, "role": user.role } 
    result = await database.users.insert_one(user_dict) 
    return { "message": "User registered successfully", "id": str(result.inserted_id) }