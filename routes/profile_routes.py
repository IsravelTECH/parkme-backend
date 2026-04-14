from fastapi import APIRouter, Depends
from database import database
from utils.auth import get_current_user
from datetime import datetime, timezone
from fastapi import UploadFile, File
import os

router = APIRouter()


async def auto_complete_bookings():
    now = datetime.now(timezone.utc)

    # ✅ update all expired bookings
    await database.bookings.update_many(
        {
            "status": "active",
            "end_time": {"$lte": now}
        },
        {
            "$set": {"status": "completed"}
        }
    )

@router.get("/profile")
async def get_profile(current_user = Depends(get_current_user)):

    await auto_complete_bookings()

    user_id = str(current_user["_id"])

    user = await database.users.find_one({"_id": current_user["_id"]})

    # ✅ parkings
    parkings = await database.parkings.find({
        "owner_id": user_id
    }).to_list(100)

    total_slots = sum(p.get("total_slots", 0) for p in parkings)

    # ✅ bookings (user side)
    bookings = await database.bookings.find({
        "user_id": user_id
    }).to_list(100)

    from datetime import datetime, timezone

    # ✅ ACTIVE BOOKINGS (time + status)
    active_bookings_data = await database.bookings.find({
        "user_id": user_id,
        "status": "active",
        "end_time": {"$gt": datetime.now(timezone.utc)}
    }).to_list(100)

    active_bookings = len(active_bookings_data)

    # ✅ EARNINGS (active + completed)
    earnings_data = await database.bookings.find({
        "owner_id": user_id,
        "status": {"$in": ["active", "completed"]}
    }).to_list(100)

    total_earnings = sum(
        b.get("total_price", 0)
        for b in earnings_data
    )

    return {
        "id": user_id,
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "profile_image": user.get("profile_image"), 
        "total_slots": total_slots,
        "total_bookings": len(bookings),
        "active_bookings": active_bookings,
        "total_earnings": total_earnings
    }

@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    user_id = str(current_user["_id"])

    os.makedirs("static/profile", exist_ok=True)  # ✅ auto create

    file_path = f"static/profile/{user_id}.png"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    image_url = f"https://parkme-backend.onrender.com/{file_path}"

    await database.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"profile_image": image_url}}
    )

    return {"message": "Uploaded", "image_url": image_url}