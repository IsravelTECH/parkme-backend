import re
from bson import ObjectId
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Depends
from passlib.context import CryptContext

from models.user_model import SignupRequest, LoginRequest, ReviewRequest
from database import database
from utils.auth import create_access_token, get_current_user, verify_token

IST = ZoneInfo("Asia/Kolkata") 

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/signup")
async def signup(user: SignupRequest):
    existing_user = await database.users.find_one({"email": user.email.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user.password)
    created_time = datetime.now(IST)

    new_user = {
        "name": user.name.strip(),
        "email": user.email.lower(),
        "phone": user.phone.strip(),
        "password": hashed_password,
        "role": "seeker",
        "created_at": created_time,
        "last_login": None,
        "login_history": []
    }

    result = await database.users.insert_one(new_user)
    token = create_access_token(str(result.inserted_id), role="seeker")

    return {
        "message": "User created successfully",
        "token": token,
        "name": new_user["name"],
        "role": "seeker",
        "created_at": created_time
    }

@router.post("/login")
async def login(data: LoginRequest):
    user = await database.users.find_one({"email": data.email.lower()})

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if not pwd_context.verify(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid password")

    login_time = datetime.now(IST)

    # Populate created_at for legacy users if absent
    if not user.get("created_at"):
        await database.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"created_at": login_time}}
        )
        user["created_at"] = login_time

    await database.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"last_login": login_time},
            "$push": {"login_history": login_time}
        }
    )

    role = user.get("role", "seeker")
    token = create_access_token(str(user["_id"]), role=role)

    return {
        "message": "Login successful",
        "token": token,
        "name": user["name"],
        "role": role,
        "created_at": user.get("created_at"),
        "login_history": user.get("login_history", []) + [login_time],
        "last_login": login_time
    }

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
    current_user=Depends(get_current_user)
):
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    review_data = {
        "user_id": str(current_user["_id"]),
        "name": current_user.get("name", "Anonymous"),
        "rating": review.rating,
        "message": review.message.strip(),
        "created_at": datetime.now(IST)
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
# ✅ Search Parking (ReDoS safe)
# =========================
@router.get("/search")
async def search_parking(query: str):
    safe_query = re.escape(query.strip())
    cursor = database.parkings.find({
        "$or": [
            {"name": {"$regex": safe_query, "$options": "i"}},
            {"address": {"$regex": safe_query, "$options": "i"}}
        ]
    })

    results = await cursor.to_list(length=100)

    for r in results:
        r["_id"] = str(r["_id"])

    return {
        "results": results
    }