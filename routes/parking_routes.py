import os
import math
import uuid
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Form, UploadFile, File, HTTPException

from database import database
from utils.auth import get_current_user
from utils.booking_utils import auto_complete_bookings

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# IST timezone
IST = ZoneInfo("Asia/Kolkata")

def format_ist(dt: datetime) -> str:
    """Convert UTC or offset-aware datetime to IST string (12-hour format)."""
    ist_time = dt.astimezone(IST)
    return ist_time.strftime("%I:%M %p")

def get_remaining_time(end_time: datetime) -> int:
    """Calculate remaining minutes until booking expiry."""
    now = datetime.now(timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    diff = end_time - now
    minutes = int(diff.total_seconds() / 60)
    return max(minutes, 0)

def serialize_booking(booking: dict) -> dict:
    created_at = booking.get("created_at")
    if created_at and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    created_str = created_at.astimezone(IST).strftime("%Y-%m-%d %I:%M %p") if created_at else "N/A"

    return {
        "_id": str(booking.get("_id")),
        "parking_id": str(booking.get("parking_id")),
        "user_id": str(booking.get("user_id")),
        "owner_id": str(booking.get("owner_id")) if booking.get("owner_id") else None,
        "parking_name": booking.get("parking_name", "N/A"),
        "parking_address": booking.get("parking_address", "N/A"),
        "vehicle_number": booking.get("vehicle_number"),
        "booking_date": booking.get("booking_date"),
        "time_range": f"{format_ist(booking['start_time'])} - {format_ist(booking['end_time'])}",
        "hours": booking.get("hours"),
        "price_per_hour": booking.get("price_per_hour"),
        "total_price": booking.get("total_price"),
        "selected_days": booking.get("selected_days"),
        "remaining_minutes": get_remaining_time(booking.get("end_time")),
        "status": booking.get("status"),
        "created_at": created_str
    }

async def save_uploaded_image(image: UploadFile, subfolder: str = "uploads") -> str:
    """Validates and saves an uploaded image safely using a random UUID filename."""
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type. Only JPEG, PNG, and WebP are allowed.")

    ext = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file extension.")

    contents = await image.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Image size exceeds maximum allowed limit of 5MB.")

    os.makedirs(subfolder, exist_ok=True)
    safe_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = f"{subfolder}/{safe_filename}"

    with open(file_path, "wb") as f:
        f.write(contents)

    return file_path

@router.delete("/delete-parking/{parking_id}")
async def delete_parking(parking_id: str, user=Depends(get_current_user)):
    parking = await database.parkings.find_one({
        "_id": ObjectId(parking_id),
        "owner_id": str(user["_id"])
    })

    if not parking:
        raise HTTPException(status_code=404, detail="Parking space not found")

    await database.parkings.delete_one({"_id": ObjectId(parking_id)})
    return {"message": "Parking deleted successfully"}

@router.get("/parkings")
async def get_all_parkings():
    parkings = []
    async for parking in database.parkings.find():
        parking["_id"] = str(parking["_id"])
        parkings.append(parking)
    return parkings

@router.post("/book-slot")
async def book_slot(data: dict, current_user=Depends(get_current_user)):
    user_id = str(current_user["_id"])
    parking_id = data.get("parking_id")
    vehicle_number = data.get("vehicle_number")
    booking_date = data.get("booking_date")
    start_time_input = data.get("start_time")
    end_time_input = data.get("end_time")
    selected_days = data.get("selected_days")

    if not all([parking_id, vehicle_number, booking_date, start_time_input, end_time_input, selected_days]):
        return {"error": "Missing required fields"}

    parking = await database.parkings.find_one({"_id": ObjectId(parking_id)})
    if not parking:
        return {"error": "Parking space not found"}

    if parking.get("available_slots", 0) <= 0:
        return {"error": "No slots currently available"}

    try:
        start_local = datetime.strptime(
            f"{booking_date} {start_time_input}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=IST)

        end_local = datetime.strptime(
            f"{booking_date} {end_time_input}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=IST)
    except ValueError:
        return {"error": "Invalid date or time format"}

    if end_local <= start_local:
        return {"error": "End time must be after start time"}

    start_datetime = start_local.astimezone(timezone.utc)
    end_datetime = end_local.astimezone(timezone.utc)

    # Use math.ceil to prevent 0 hours (e.g. 45 min parking)
    duration_seconds = (end_datetime - start_datetime).total_seconds()
    hours = max(1, math.ceil(duration_seconds / 3600))

    # Day validation
    booking_day = start_local.strftime("%a")
    available_days = parking.get("available_days", [])

    for day in selected_days:
        if day not in available_days:
            return {"error": f"{day} is not available for this parking space"}

    if booking_day not in selected_days:
        return {"error": f"Booking date ({booking_day}) must match selected days"}

    price_per_hour = parking.get("price_per_hour", 0)
    total_price = hours * price_per_hour

    booking = {
        "parking_id": str(parking_id),
        "user_id": user_id,
        "owner_id": parking.get("owner_id"),
        "parking_name": parking.get("name"),
        "parking_address": parking.get("address"),
        "image_url": parking.get("image"),
        "vehicle_number": str(vehicle_number).strip().upper(),
        "booking_date": booking_date,
        "start_time": start_datetime,
        "end_time": end_datetime,
        "hours": hours,
        "price_per_hour": price_per_hour,
        "total_price": total_price,
        "selected_days": selected_days,
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }

    result = await database.bookings.insert_one(booking)
    booking["_id"] = result.inserted_id

    return {
        "message": "Booking initiated successfully",
        "booking_details": serialize_booking(booking)
    }

@router.put("/complete-booking/{booking_id}")
async def complete_booking(booking_id: str, user=Depends(get_current_user)):
    booking = await database.bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        return {"error": "Booking not found"}

    if booking["status"] == "active":
        return {"message": "Booking is already active"}

    # Atomic slot decrement
    update_res = await database.parkings.update_one(
        {"_id": ObjectId(booking["parking_id"]), "available_slots": {"$gt": 0}},
        {"$inc": {"available_slots": -1}}
    )

    if update_res.modified_count == 0:
        return {"error": "No available slots to confirm this booking"}

    await database.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "active"}}
    )

    return {"message": "Booking confirmed & slot reserved"}

@router.get("/nearby")
async def nearby(
    lat: float,
    lng: float,
    max_distance: int = 5000,
    max_price: int = 500,
    search: str = ""
):
    await auto_complete_bookings()

    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [lng, lat]
                },
                "distanceField": "distance",
                "maxDistance": max_distance,
                "spherical": True
            }
        },
        {
            "$match": {
                "price_per_hour": {"$lte": max_price},
                "available_slots": {"$gt": 0}
            }
        }
    ]

    if search.strip():
        import re
        safe_search = re.escape(search.strip())
        pipeline.append({
            "$match": {
                "$or": [
                    {"name": {"$regex": safe_search, "$options": "i"}},
                    {"address": {"$regex": safe_search, "$options": "i"}}
                ]
            }
        })

    pipeline.append({"$sort": {"distance": 1}})

    results = await database.parkings.aggregate(pipeline).to_list(100)

    response = []
    for r in results:
        response.append({
            "id": str(r["_id"]),
            "parking_id": str(r["_id"]),
            "name": r.get("name"),
            "address": r.get("address"),
            "lat": r["location"]["coordinates"][1],
            "lng": r["location"]["coordinates"][0],
            "price_per_hour": r.get("price_per_hour"),
            "distance": round(r.get("distance", 0)),
            "available_slots": r.get("available_slots"),
            "image": r.get("image"),
            "features": r.get("features", []),
            "available_days": r.get("available_days", []),
            "added_by": r.get("added_by", {})
        })

    return {"results": response}

@router.post("/add-parking")
async def add_parking(
    name: str = Form(...),
    city: str = Form(...),
    landmark: str = Form(...),
    address: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    price_per_hour: int = Form(...),
    total_slots: int = Form(...),
    available_slots: int = Form(...),
    features: List[str] = Form(...),
    available_days: List[str] = Form(...),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    user=Depends(get_current_user)
):
    try:
        default_img = "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80"
        if image_url and image_url.strip():
            file_path = image_url.strip()
        elif image and image.filename:
            file_path = await save_uploaded_image(image, subfolder="uploads")
        else:
            file_path = default_img

        parking_doc = {
            "name": name.strip(),
            "city": city.strip(),
            "landmark": landmark.strip(),
            "address": address.strip(),
            "location": {
                "type": "Point",
                "coordinates": [lng, lat]
            },
            "price_per_hour": price_per_hour,
            "total_slots": total_slots,
            "available_slots": available_slots,
            "features": features,
            "available_days": available_days,
            "image": file_path,
            "images": [file_path],
            "owner_id": str(user["_id"]),
            "added_by": {
                "name": user.get("name"),
                "email": user.get("email")
            }
        }

        result = await database.parkings.insert_one(parking_doc)

        return {
            "message": "Parking added successfully",
            "id": str(result.inserted_id),
            "parking_id": str(result.inserted_id),
            "image": file_path
        }
    except HTTPException:
        raise
    except Exception as e:
        print("ERROR adding parking:", str(e))
        raise HTTPException(status_code=500, detail="Failed to add parking")

@router.get("/my-dashboard")
async def get_my_dashboard(current_user: dict = Depends(get_current_user)):
    await auto_complete_bookings()

    user_id = str(current_user["_id"])
    parkings = await database.parkings.find({"owner_id": user_id}).to_list(100)

    total_slots = 0
    total_active = 0
    total_earnings = 0
    parking_list = []

    for p in parkings:
        bookings = await database.bookings.find({
            "parking_id": str(p["_id"])
        }).to_list(100)

        active = sum(1 for b in bookings if b.get("status") == "active")
        earnings = sum(
            b.get("total_price", 0)
            for b in bookings
            if b.get("status") in ["active", "completed"]
        )

        total_slots += p.get("total_slots", 0)
        total_active += active
        total_earnings += earnings

        parking_list.append({
            "id": str(p["_id"]),
            "parking_id": str(p["_id"]),
            "name": p.get("name"),
            "city": p.get("city"),
            "image": p.get("image"),
            "price": p.get("price_per_hour"),
            "landmark": p.get("landmark"),
            "address": p.get("address"),
            "features": p.get("features", []),
            "available_days": p.get("available_days", []),
            "lat": p["location"]["coordinates"][1],
            "lng": p["location"]["coordinates"][0],
            "total_slots": p.get("total_slots"),
            "available_slots": p.get("available_slots"),
            "active_bookings": active,
            "earnings": earnings
        })

    return {
        "total_slots": total_slots,
        "active_bookings": total_active,
        "total_earnings": total_earnings,
        "parkings": parking_list
    }

@router.put("/update-parking/{space_id}")
async def update_parking(
    space_id: str,
    name: str = Form(...),
    city: str = Form(...),
    landmark: str = Form(...),
    address: str = Form(...),
    slots: int = Form(...),
    price_per_hour: float = Form(...),
    days: List[str] = Form(...),
    features: List[str] = Form(...),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    user=Depends(get_current_user)
):
    parking_space = await database.parkings.find_one({
        "_id": ObjectId(space_id),
        "owner_id": str(user["_id"])
    })

    if not parking_space:
        raise HTTPException(status_code=404, detail="Parking space not found")

    image_path = parking_space.get("image")
    if image_url and image_url.strip():
        image_path = image_url.strip()
    elif image and image.filename:
        image_path = await save_uploaded_image(image, subfolder="uploads")

    # Reconcile available slots based on active bookings
    active_count = await database.bookings.count_documents({
        "parking_id": space_id,
        "status": "active"
    })
    new_available_slots = max(0, slots - active_count)

    update_fields = {
        "name": name.strip(),
        "city": city.strip(),
        "landmark": landmark.strip(),
        "address": address.strip(),
        "total_slots": slots,
        "available_slots": new_available_slots,
        "price_per_hour": price_per_hour,
        "available_days": days,
        "features": features,
        "image": image_path,
        "images": [image_path]
    }
    if lat is not None and lng is not None:
        update_fields["lat"] = lat
        update_fields["lng"] = lng

    await database.parkings.update_one(
        {"_id": ObjectId(space_id)},
        {"$set": update_fields}
    )

    updated_parking = await database.parkings.find_one({"_id": ObjectId(space_id)})

    return {
        "message": "Parking space updated successfully",
        "parking_space": {
            "id": str(updated_parking["_id"]),
            "parking_id": str(updated_parking["_id"]),
            "name": updated_parking["name"],
            "city": updated_parking["city"],
            "landmark": updated_parking["landmark"],
            "address": updated_parking["address"],
            "slots": updated_parking["total_slots"],
            "available_slots": updated_parking["available_slots"],
            "price_per_hour": updated_parking["price_per_hour"],
            "days": updated_parking.get("available_days", []),
            "features": updated_parking.get("features", []),
            "image_url": updated_parking.get("image")
        }
    }