from fastapi import APIRouter, Depends
from models.parking_model import Parking
from database import database
from auth import require_role
from datetime import datetime
from models.booking_model import Booking
from bson import ObjectId
from fastapi import HTTPException

router = APIRouter()

@router.post("/create-parking")
async def create_parking(
    parking: Parking,
    user=Depends(require_role("owner"))
):
    parking_dict = parking.dict()
    parking_dict["owner_id"] = user["sub"]
    parking_dict["available_slots"] = parking.total_slots

    result = await database.parkings.insert_one(parking_dict)

    return {
        "message": "Parking created successfully",
        "id": str(result.inserted_id)
    }

@router.get("/parkings")
async def get_all_parkings():
    parkings = []
    async for parking in database.parkings.find():
        parking["_id"] = str(parking["_id"])
        parkings.append(parking)

    return parkings


@router.post("/book-slot")
async def book_slot(
    booking: Booking,
    user=Depends(require_role("seeker"))
):
    parking = await database.parkings.find_one(
        {"_id": ObjectId(booking.parking_id)}
    )

    if not parking:
        raise HTTPException(status_code=404, detail="Parking not found")

    if parking["available_slots"] <= 0:
        raise HTTPException(status_code=400, detail="No slots available")

    existing_booking = await database.bookings.find_one({
        "parking_id": booking.parking_id,
        "user_id": user["sub"]
    })

    if existing_booking:
        raise HTTPException(
            status_code=400,
            detail="You have already booked this parking"
        )

    # 💰 Calculate total price
    total_price = booking.hours * parking["price_per_hour"]

    # Reduce slot count
    await database.parkings.update_one(
        {"_id": ObjectId(booking.parking_id)},
        {"$inc": {"available_slots": -1}}
    )

    booking_data = {
        "parking_id": booking.parking_id,
        "user_id": user["sub"],
        "hours": booking.hours,
        "total_price": total_price,
        "booking_time": datetime.utcnow()
    }

    result = await database.bookings.insert_one(booking_data)

    return {
        "message": "Booking successful",
        "booking_id": str(result.inserted_id),
        "total_price": total_price
    }

@router.get("/my-bookings")
async def my_bookings(user=Depends(require_role("seeker"))):
    bookings = []

    async for booking in database.bookings.find(
        {"user_id": user["sub"]}
    ):
        parking = await database.parkings.find_one(
            {"_id": ObjectId(booking["parking_id"])}
        )

        bookings.append({
            "booking_id": str(booking["_id"]),
            "parking_id": booking["parking_id"],
            "location": parking["location"] if parking else None,
            "price_per_hour": parking["price_per_hour"] if parking else None
        })

    return bookings

@router.post("/checkout/{booking_id}")
async def checkout(
    booking_id: str,
    user=Depends(require_role("seeker"))
):
    booking = await database.bookings.find_one(
        {"_id": ObjectId(booking_id)}
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking["user_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your booking")

    if booking.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Already checked out")

    # Mark completed
    await database.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "completed"}}
    )

    # Increase slot
    await database.parkings.update_one(
        {"_id": ObjectId(booking["parking_id"])},
        {"$inc": {"available_slots": 1}}
    )

    return {"message": "Checked out successfully"}

@router.get("/admin-dashboard")
async def admin_dashboard(user=Depends(require_role("admin"))):

    total_users = await database.users.count_documents({})
    total_owners = await database.users.count_documents({"role": "owner"})
    total_seekers = await database.users.count_documents({"role": "seeker"})

    total_parkings = await database.parkings.count_documents({})
    total_bookings = await database.bookings.count_documents({})
    active_bookings = await database.bookings.count_documents({"status": "active"})
    completed_bookings = await database.bookings.count_documents({"status": "completed"})

    total_revenue = 0
    async for booking in database.bookings.find():
        total_revenue += booking.get("total_price", 0)

    return {
        "total_users": total_users,
        "total_owners": total_owners,
        "total_seekers": total_seekers,
        "total_parkings": total_parkings,
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "completed_bookings": completed_bookings,
        "total_revenue": total_revenue
    }