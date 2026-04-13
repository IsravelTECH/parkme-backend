from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from models.user_model import SignupRequest
from models.user_model import LoginRequest  
from models.user_model import ReviewRequest
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
from typing import Optional 

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



# =========================
# ✅ POST Review (Logged User)
# =========================
@router.post("/reviews")
async def create_review(
    review: ReviewRequest,
    user=Depends(verify_token)  # Get logged-in user
    
):

    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    user_data = await database.users.find_one({"_id": ObjectId(user["sub"])})
    review_data = {
        "user_id": user["sub"],
        "name": user_data["name"],
        "rating": review.rating,
        "message": review.message,
        "created_at": datetime.utcnow()
    }

    result = await database.reviews.insert_one(review_data)

    return {
        "message": "Review submitted successfully",
        "review_id": str(result.inserted_id)
    }


# =========================
# ✅ GET ALL Reviews
# =========================
@router.get("/reviews")
async def get_all_reviews():

    reviews_cursor = database.reviews.find().sort("created_at", -1)

    reviews = []

    async for review in reviews_cursor:
        reviews.append({
            "id": str(review["_id"]),
            "name": review["name"],
            "rating": review["rating"],
            "message": review["message"],
            "created_at": review["created_at"]
        })

    return {
        "total": len(reviews),
        "reviews": reviews
    }

# =========================
# ✅ DELETE ALL REVIEWS (Optional)
# =========================
@router.delete("/reviews/delete-all")
async def delete_all_reviews():
    await database.reviews.delete_many({})
    return {"message": "All reviews deleted"}

@router.get("/search")
async def search_parking(query: str):

    cursor = database.parkings.find({
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"address": {"$regex": query, "$options": "i"}}
        ]
    })

    results = await cursor.to_list(length=100)

    # 🔥 Convert ObjectId to string
    for r in results:
        r["_id"] = str(r["_id"])

    return {
        "results": results
    }