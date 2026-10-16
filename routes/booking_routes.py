import os
import stripe
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import database
from utils.auth import get_current_user

router = APIRouter()

def parse_date(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return datetime.min

def format_time(dt):
    dt = parse_date(dt)
    return dt.strftime("%Y-%m-%d %H:%M") if dt != datetime.min else "N/A"

@router.get("/user-booking-dashboard")
async def get_user_dashboard(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])

    # Fetch all bookings for this user via async Motor
    bookings = await database.bookings.find({"user_id": user_id}).to_list(length=200)

    # Sort latest first
    bookings = sorted(
        bookings,
        key=lambda x: parse_date(x.get("start_time")),
        reverse=True
    )

    # Deduplicate if duplicate records exist
    unique_map = {}
    for b in bookings:
        key = f"{b.get('start_time')}_{b.get('end_time')}_{b.get('vehicle_number')}_{b.get('parking_id')}"
        if key not in unique_map:
            unique_map[key] = b

    bookings = list(unique_map.values())

    # Attach live parking details
    for b in bookings:
        parking = None
        if b.get("parking_id"):
            try:
                parking = await database.parkings.find_one({"_id": ObjectId(b["parking_id"])})
            except Exception:
                parking = None

        if parking:
            b["parking_name"] = parking.get("name", "N/A")
            b["parking_address"] = parking.get("address", "N/A")
            b["image_url"] = parking.get("image")
        else:
            b["parking_name"] = b.get("parking_name", "N/A")
            b["parking_address"] = b.get("parking_address", "N/A")
            b["image_url"] = b.get("image_url", None)

    # Filter out records without valid timestamps
    bookings = [b for b in bookings if b.get("start_time") and b.get("end_time")]

    total_bookings = len(bookings)
    cancelled_count = len([b for b in bookings if (b.get("status") or "").lower() == "cancelled"])
    pending_count = len([b for b in bookings if (b.get("status") or "").lower() == "pending"])
    total_spent = sum([
        float(b.get("total_price", 0))
        for b in bookings
        if (b.get("status") or "").lower() != "cancelled"
    ])

    active_bookings = []
    for b in bookings:
        if (b.get("status") or "").lower() == "active":
            active_bookings.append({
                "booking_id": str(b.get("_id")),
                "parking_name": b.get("parking_name", "N/A"),
                "address": b.get("parking_address", "N/A"),
                "vehicle": b.get("vehicle_number", "N/A"),
                "time": f"{format_time(b.get('start_time'))} - {format_time(b.get('end_time'))}",
                "image": b.get("image_url"),
                "status": b.get("status")
            })

    history = []
    for b in bookings:
        status = (b.get("status") or "").lower()
        if status not in ["completed", "cancelled", "pending"]:
            continue

        history.append({
            "booking_id": str(b.get("_id")),
            "parking_name": b.get("parking_name", "N/A"),
            "vehicle": b.get("vehicle_number", "N/A"),
            "time": f"{format_time(b.get('start_time'))} - {format_time(b.get('end_time'))}",
            "amount": float(b.get("total_price", 0)),
            "status": b.get("status"),
            "image": b.get("image_url")
        })

    return {
        "summary": {
            "total_bookings": total_bookings,
            "cancelled_bookings": cancelled_count,
            "pending_bookings": pending_count,
            "total_spent": total_spent
        },
        "active_booking": active_bookings,
        "history": history
    }

@router.put("/cancel-booking/{booking_id}")
async def cancel_booking(booking_id: str, user=Depends(get_current_user)):
    try:
        obj_id = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID")

    booking = await database.bookings.find_one({
        "_id": obj_id,
        "user_id": str(user["_id"])
    })

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    status = (booking.get("status") or "").lower()
    if status == "cancelled":
        raise HTTPException(status_code=400, detail="Booking is already cancelled")
    if status == "completed":
        raise HTTPException(status_code=400, detail="Completed bookings cannot be cancelled")

    parking_id = booking.get("parking_id")

    # Mark booking cancelled
    await database.bookings.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc)
            }
        }
    )

    # CRITICAL FIX: Only replenish available_slots if the booking was ACTIVE
    if status == "active" and parking_id:
        try:
            await database.parkings.update_one(
                {"_id": ObjectId(parking_id)},
                {"$inc": {"available_slots": 1}}
            )
        except Exception as e:
            print(f"Error restoring slot on cancellation for parking {parking_id}: {e}")

    return {"message": "Booking cancelled successfully"}

@router.get("/verify-payment/{session_id}")
async def verify_payment(session_id: str):
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        return {"error": "Stripe configuration missing"}

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        return {"error": f"Invalid checkout session: {str(e)}"}

    if session.payment_status != "paid":
        return {"error": "Payment has not been completed"}

    booking_id = session.metadata.get("booking_id") if session.metadata else None
    if not booking_id:
        return {"error": "Booking ID missing from session metadata"}

    try:
        booking = await database.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        return {"error": "Invalid booking ID in session"}

    if not booking:
        return {"error": "Booking not found"}

    parking = await database.parkings.find_one({"_id": ObjectId(booking["parking_id"])})
    parking_name = parking.get("name") if parking else "N/A"
    location = parking.get("address") if parking else "N/A"
    start_time = parse_date(booking.get("start_time"))
    end_time = parse_date(booking.get("end_time"))

    # If already active, return confirmed details
    if booking.get("status") == "active":
        return {
            "message": "Payment verified & booking is active",
            "booking_details": {
                "booking_id": str(booking["_id"]),
                "parking_name": parking_name,
                "location": location,
                "date": booking.get("booking_date"),
                "time": f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                "payment_method": "Card (Stripe)",
                "amount_paid": booking.get("total_price"),
                "vehicle_number": booking.get("vehicle_number"),
                "status": "active"
            }
        }

    # Decrement available slots atomically
    await database.parkings.update_one(
        {
            "_id": ObjectId(booking["parking_id"]),
            "available_slots": {"$gt": 0}
        },
        {"$inc": {"available_slots": -1}}
    )

    # Activate booking
    await database.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "active", "paid_at": datetime.now(timezone.utc)}}
    )

    return {
        "message": "Payment verified & booking activated",
        "booking_details": {
            "booking_id": str(booking["_id"]),
            "parking_name": parking_name,
            "location": location,
            "date": booking.get("booking_date"),
            "time": f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
            "payment_method": "Card (Stripe)",
            "amount_paid": booking.get("total_price"),
            "vehicle_number": booking.get("vehicle_number"),
            "status": "active"
        }
    }