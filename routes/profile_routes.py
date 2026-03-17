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

    return {
        "id": str(current_user["_id"]),
        "name": current_user["name"],
        "email": current_user["email"],
        "total_slots": len(slots),
        "total_bookings": len(bookings)
    }