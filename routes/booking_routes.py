from fastapi import APIRouter, Depends
from pymongo import MongoClient
from bson import ObjectId
import os
from datetime import datetime
from utils.auth import get_current_user

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

    total_spent = sum([
        float(b.get("total_price", 0))
        for b in bookings
        if (b.get("status") or "").lower() != "cancelled"
    ])

    # =========================
    # ✅ ACTIVE BOOKINGS (ALL ACTIVE)
    # =========================
    active_bookings = []

    for b in bookings:
        if (b.get("status") or "").lower() == "active":
            active_bookings.append({
                "parking_name": b.get("parking_name", "N/A"),
                "address": b.get("parking_address", "N/A"),
                "vehicle": b.get("vehicle_number", "N/A"),
                "time": f"{format_time(b.get('start_time'))} - {format_time(b.get('end_time'))}",
                "image": b.get("image_url"),
                "status": b.get("status")
            })

    # =========================
    # ✅ HISTORY (ONLY COMPLETED)
    # =========================
    history = []

    for b in bookings:
        if (b.get("status") or "").lower() != "completed":
            continue

        history.append({
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
            "cancelled_bookings": cancelled_count,
            "total_spent": total_spent
        },
        "active_booking": active_bookings,  # 🔥 NOW LIST
        "history": history
    }