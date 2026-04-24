from fastapi import APIRouter, Depends , HTTPException
from pymongo import MongoClient
from bson import ObjectId
import os
import stripe
from datetime import datetime
from utils.auth import get_current_user
from database import database


router = APIRouter()

client = MongoClient(os.getenv("MONGO_URL"))
db = client[os.getenv("DATABASE_NAME")]

bookings_collection = db["bookings"]
parkings_collection = db["parkings"]


# =========================
# ✅ SAFE DATE PARSER
# =========================
def parse_date(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except:
        return datetime.min


# =========================
# ✅ FORMAT TIME
# =========================
def format_time(dt):
    dt = parse_date(dt)
    return dt.strftime("%Y-%m-%d %H:%M") if dt != datetime.min else "N/A"


# =========================
# ✅ DASHBOARD API
# =========================
@router.get("/user-booking-dashboard")
def get_user_dashboard(current_user: dict = Depends(get_current_user)):

    user_id = str(current_user["_id"])

    # =========================
    # ✅ FETCH BOOKINGS
    # =========================
    bookings = list(bookings_collection.find({"user_id": user_id}))

    # =========================
    # ✅ SORT (LATEST FIRST)
    # =========================
    bookings = sorted(
        bookings,
        key=lambda x: parse_date(x.get("start_time")),
        reverse=True
    )

    # =========================
    # ✅ REMOVE DUPLICATES
    # =========================
    unique_map = {}
    for b in bookings:
        key = f"{b.get('start_time')}_{b.get('end_time')}_{b.get('vehicle_number')}_{b.get('parking_id')}"
        if key not in unique_map:
            unique_map[key] = b

    bookings = list(unique_map.values())

    # =========================
    # ✅ ATTACH PARKING DETAILS
    # =========================
    for b in bookings:
        parking = None

        try:
            if b.get("parking_id"):
                parking = parkings_collection.find_one({
                    "_id": ObjectId(b.get("parking_id"))
                })
        except:
            parking = None

        if parking:
            b["parking_name"] = parking.get("name", "N/A")
            b["parking_address"] = parking.get("address", "N/A")
            b["image_url"] = parking.get("image")
        else:
            b["parking_name"] = b.get("parking_name", "N/A")
            b["parking_address"] = b.get("parking_address", "N/A")
            b["image_url"] = b.get("image_url", None)

    # =========================
    # ✅ REMOVE INVALID
    # =========================
    bookings = [
        b for b in bookings
        if b.get("start_time") and b.get("end_time")
    ]

    # =========================
    # ✅ SUMMARY
    # =========================
    total_bookings = len(bookings)

    cancelled_count = len([
        b for b in bookings
        if (b.get("status") or "").lower() == "cancelled"
    ])

    pending_count = len([
        b for b in bookings
        if (b.get("status") or "").lower() == "pending"
    ])

    total_spent = sum([
        float(b.get("total_price", 0))
        for b in bookings
        if (b.get("status") or "").lower() != "cancelled"
    ])

    # =========================
    # ✅ ACTIVE BOOKINGS
    # =========================
    active_bookings = []

    for b in bookings:
        if (b.get("status") or "").lower() == "active":
            active_bookings.append({
                "booking_id": str(b.get("_id")),  # ✅ added
                "parking_name": b.get("parking_name", "N/A"),
                "address": b.get("parking_address", "N/A"),
                "vehicle": b.get("vehicle_number", "N/A"),
                "time": f"{format_time(b.get('start_time'))} - {format_time(b.get('end_time'))}",
                "image": b.get("image_url"),
                "status": b.get("status")
            })

    # =========================
    # ✅ HISTORY (COMPLETED + CANCELLED)
    # =========================
    history = []

    for b in bookings:
        status = (b.get("status") or "").lower()

        if status not in ["completed", "cancelled", "pending"]:
            continue

        history.append({
            "booking_id": str(b.get("_id")),  # ✅ added
            "parking_name": b.get("parking_name", "N/A"),
            "vehicle": b.get("vehicle_number", "N/A"),
            "time": f"{format_time(b.get('start_time'))} - {format_time(b.get('end_time'))}",
            "amount": float(b.get("total_price", 0)),
            "status": b.get("status"),
            "image": b.get("image_url")
        })

    # =========================
    # ✅ FINAL RESPONSE
    # =========================
    return {
        "summary": {
            "total_bookings": total_bookings,
            "cancelled_bookings": cancelled_count,  # ✅ already correct
            "pending_bookings": pending_count, 
            "total_spent": total_spent
        },
        "active_booking": active_bookings,
        "history": history
    }

@router.put("/cancel-booking/{booking_id}")
async def cancel_booking(booking_id: str, user=Depends(get_current_user)):

    booking = await database.bookings.find_one({
        "_id": ObjectId(booking_id),
        "user_id": str(user["_id"])
    })

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if (booking.get("status") or "").lower() == "cancelled":
        raise HTTPException(status_code=400, detail="Already cancelled")

    parking_id = booking.get("parking_id")

    # ✅ Update booking
    await database.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": datetime.utcnow()
            }
        }
    )

    # ✅ ADD SLOT BACK
    if parking_id:
        await database.parkings.update_one(
            {"_id": ObjectId(parking_id)},
            {"$inc": {"available_slots": 1}}
        )

    return {"message": "Booking cancelled successfully"}


@router.get("/verify-payment/{session_id}")
async def verify_payment(session_id: str):

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status != "paid":
        return {"error": "Payment not completed"}

    # ✅ FIXED
    booking_id = session.metadata["booking_id"] if session.metadata and "booking_id" in session.metadata else None

    if not booking_id:
        return {"error": "Booking ID missing"}

    booking = await database.bookings.find_one({"_id": ObjectId(booking_id)})

    if not booking:
        return {"error": "Booking not found"}

    if booking.get("status") != "active":
        await database.bookings.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"status": "active"}}
        )
        booking["status"] = "active"

    parking = await database.parkings.find_one({
        "_id": ObjectId(booking["parking_id"])
    })

    parking_name = parking.get("name") if parking else "N/A"
    location = parking.get("address") if parking else "N/A"

    start_time = booking.get("start_time")
    end_time = booking.get("end_time")

    return {
        "message": "Payment verified & booking activated",
        "booking_details": {
            "booking_id": str(booking["_id"]),
            "parking_name": parking_name,
            "location": location,
            "date": start_time.strftime("%Y-%m-%d"),
            "time": f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
            "payment_method": "Card (Stripe)",
            "amount_paid": booking.get("total_price"),
            "vehicle_number": booking.get("vehicle_number"),
            "status": booking.get("status")
        }
    }