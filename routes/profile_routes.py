import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from database import database
from utils.auth import get_current_user
from utils.booking_utils import auto_complete_bookings

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

@router.get("/profile")
async def get_profile(current_user=Depends(get_current_user)):
    await auto_complete_bookings()

    user_id = str(current_user["_id"])
    user = await database.users.find_one({"_id": current_user["_id"]})

    # Total parking spaces and slots owned
    parkings = await database.parkings.find({"owner_id": user_id}).to_list(100)
    total_slots = sum(p.get("total_slots", 0) for p in parkings)

    # All bookings by user
    bookings = await database.bookings.find({"user_id": user_id}).to_list(100)

    # Active bookings
    now = datetime.now(timezone.utc)
    active_bookings_data = await database.bookings.find({
        "user_id": user_id,
        "status": "active",
        "end_time": {"$gt": now}
    }).to_list(100)
    active_bookings = len(active_bookings_data)

    # Earnings for owned parking spaces
    earnings_data = await database.bookings.find({
        "owner_id": user_id,
        "status": {"$in": ["active", "completed"]}
    }).to_list(100)

    total_earnings = sum(b.get("total_price", 0) for b in earnings_data)

    return {
        "id": user_id,
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "role": user.get("role", "seeker"),
        "profile_image": user.get("profile_image"), 
        "total_slots": total_slots,
        "total_bookings": len(bookings),
        "active_bookings": active_bookings,
        "total_earnings": total_earnings
    }

@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    # Validate MIME type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type. Only JPEG, PNG, and WebP are allowed.")

    # Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file extension.")

    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Image size exceeds maximum allowed limit of 5MB.")

    user_id = str(current_user["_id"])
    os.makedirs("static/profile", exist_ok=True)

    # Safe file path
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = f"static/profile/{filename}"

    with open(file_path, "wb") as f:
        f.write(contents)

    backend_url = os.getenv("BACKEND_URL", "https://parkme-backend.onrender.com").rstrip("/")
    image_url = f"{backend_url}/{file_path}"

    await database.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"profile_image": image_url}}
    )

    return {"message": "Uploaded successfully", "image_url": image_url}