from fastapi import APIRouter, Depends
from database import database
from utils.auth import get_current_user

router = APIRouter()

@router.get("/profile")
async def get_profile(current_user = Depends(get_current_user)):

    user_id = current_user["_id"]

    # user details
    user = await database.users.find_one({"_id": user_id})

    # user parking slots
    slots = await database.slots.find({"owner_id": user_id}).to_list(100)

    # booking history
    bookings = await database.bookings.find({"user_id": user_id}).to_list(100)

    # ✅ Active bookings (example: status = "active")
    active_bookings = await database.bookings.find({
        "user_id": user_id,
        "status": "active"
    }).to_list(100)

    # ✅ Total earnings (from slots owned by user)
    earnings = await database.bookings.find({
        "owner_id": user_id,
        "status": "completed"
    }).to_list(100)

    total_earnings = sum(b.get("amount", 0) for b in earnings)

    return {
        "id": str(user_id),
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone"),  # ✅ added
        "total_slots": len(slots),
        "total_bookings": len(bookings),
        "active_bookings": len(active_bookings),  # ✅ added
        "total_earnings": total_earnings  # ✅ added
    }