from fastapi import APIRouter, Depends , Query , Form , UploadFile , File 
from pydantic import BaseModel
from pytest import Session 
from routes.profile_routes import auto_complete_bookings
from database import database
from auth import require_role 
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from fastapi import HTTPException
from utils.auth import get_current_user
import os
from typing import List, Optional 



router = APIRouter()

class DeleteRequest(BaseModel):
    ids: List[int]


# ✅ IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


# ✅ Convert UTC → IST string (12-hour format)
def format_ist(dt):
    ist_time = dt.astimezone(IST)
    return ist_time.strftime("%I:%M %p")  # 10:00 AM


# ✅ Countdown (minutes left)
def get_remaining_time(end_time):
    now = datetime.now(timezone.utc)
    diff = end_time - now
    minutes = int(diff.total_seconds() / 60)
    return max(minutes, 0)


# ✅ Serializer
def serialize_booking(booking):
    return {
        "_id": str(booking.get("_id")),
        "parking_id": str(booking.get("parking_id")),
        "user_id": str(booking.get("user_id")),
        "owner_id": str(booking.get("owner_id")) if booking.get("owner_id") else None,

        "vehicle_number": booking.get("vehicle_number"),
        "booking_date": booking.get("booking_date"),

        # ✅ Correct time display
        "time_range": f"{format_ist(booking['start_time'])} - {format_ist(booking['end_time'])}",

        "hours": booking.get("hours"),
        "price_per_hour": booking.get("price_per_hour"),
        "total_price": booking.get("total_price"),

        "selected_days": booking.get("selected_days"),

        # ✅ Live countdown
        "remaining_minutes": get_remaining_time(booking.get("end_time")),

        "status": booking.get("status"),
        "created_at": booking.get("created_at").astimezone(IST).strftime("%Y-%m-%d %I:%M %p")
    }

async def auto_complete_bookings():
    now = datetime.now(timezone.utc)

    expired = await database.bookings.find({
        "status": "active",
        "end_time": {"$lte": now}
    }).to_list(100)

    for b in expired:
        # ✅ Mark completed
        await database.bookings.update_one(
            {"_id": b["_id"]},
            {"$set": {"status": "completed"}}
        )

        # ✅ RETURN SLOT BACK
        await database.parkings.update_one(
            {"_id": ObjectId(b["parking_id"])},
            {"$inc": {"available_slots": 1}}
        )

@router.delete("/delete-parking/{parking_id}")
async def delete_parking(parking_id: str, user=Depends(get_current_user)):

    parking = await database.parkings.find_one({
        "_id": ObjectId(parking_id),
        "owner_id": str(user["_id"])
    })

    if not parking:
        raise HTTPException(status_code=404, detail="Parking not found")

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
async def book_slot(data: dict, current_user = Depends(get_current_user)):

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
        return {"error": "Parking not found"}

    if parking.get("available_slots", 0) <= 0:
        return {"error": "No slots available"}

    # ✅ STEP 1: Parse as IST (NOT UTC ❗)
    start_local = datetime.strptime(
        f"{booking_date} {start_time_input}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=IST)

    end_local = datetime.strptime(
        f"{booking_date} {end_time_input}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=IST)

    if end_local <= start_local:
        return {"error": "End time must be after start time"}

    # ✅ STEP 2: Convert to UTC for DB storage
    start_datetime = start_local.astimezone(timezone.utc)
    end_datetime = end_local.astimezone(timezone.utc)

    hours = int((end_datetime - start_datetime).total_seconds() / 3600)

    # ✅ Day validation
    booking_day = start_local.strftime("%a")
    available_days = parking.get("available_days", [])

    for day in selected_days:
        if day not in available_days:
            return {"error": f"{day} is not available"}

    if booking_day not in selected_days:
        return {"error": f"Booking date must match selected_days"}

    price_per_hour = parking.get("price_per_hour", 0)
    total_price = hours * price_per_hour

    owner_id = parking.get("owner_id")

    booking = {
    "parking_id": parking_id,
    "user_id": user_id,
    "owner_id": owner_id,

    # ✅ ADD THESE 3 LINES (VERY IMPORTANT)
    "parking_name": parking.get("name"),
    "parking_address": parking.get("address"),
    "image_url": parking.get("image"),
        "vehicle_number": vehicle_number,

        "booking_date": booking_date,
        "start_time": start_datetime,  # stored UTC
        "end_time": end_datetime,

        "hours": hours,
        "price_per_hour": price_per_hour,
        "total_price": total_price,

        "selected_days": selected_days,

        "status": "active",
        "created_at": datetime.now(timezone.utc)
    }

    result = await database.bookings.insert_one(booking)
    booking["_id"] = result.inserted_id

    await database.parkings.update_one(
        {"_id": ObjectId(parking_id)},
        {"$inc": {"available_slots": -1}}
    )

    return {
        "message": "Booking successful",
        "booking_details": serialize_booking(booking)
    }

@router.put("/complete-booking/{booking_id}")
async def complete_booking(booking_id: str):

    booking = await database.bookings.find_one({"_id": ObjectId(booking_id)})

    if not booking:
        return {"error": "Booking not found"}

    # ✅ update status
    await database.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "completed"}}
    )

    # ✅ increase available slots back
    await database.parkings.update_one(
        {"_id": ObjectId(booking["parking_id"])},
        {"$inc": {"available_slots": 1}}
    )

    return {"message": "Booking completed"}


@router.get("/nearby")
async def nearby(
    lat: float,
    lng: float,
    max_distance: int = 3000,
    max_price: int = 500,
    search: str = ""
):
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

    # ✅ SEARCH FILTER
    if search:
        pipeline.append({
            "$match": {
                "$or": [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"address": {"$regex": search, "$options": "i"}}
                ]
            }
        })

    await auto_complete_bookings()
    
    pipeline.append({"$sort": {"distance": 1}})

    results = await database.parkings.aggregate(pipeline).to_list(100)

    response = []
    for r in results:
        response.append({
            # ✅ BOTH IDs
            "id": str(r["_id"]),              # UI use
            "parking_id": str(r["_id"]),      # API use (booking)

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

    image: UploadFile = File(...),

    user=Depends(get_current_user)
):

    try:
        # ✅ Create uploads folder if not exists
        os.makedirs("uploads", exist_ok=True)

        # ✅ Save image
        file_path = f"uploads/{image.filename}"
        with open(file_path, "wb") as f:
            f.write(await image.read())

        # ✅ Prepare DB document
        parking_doc = {
    "name": name,
    "city": city,
    "landmark": landmark,
    "address": address,

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

    # ✅ ADD THIS (CRITICAL FIX)
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

    except Exception as e:
        print("ERROR:", str(e))
        return {"error": str(e)}
    
@router.get("/my-dashboard")
async def get_my_dashboard(current_user: dict = Depends(get_current_user)):

    await auto_complete_bookings()

    user_id = str(current_user["_id"])

    parkings = await database.parkings.find({
        "owner_id": user_id
    }).to_list(100)

    total_slots = 0
    total_active = 0
    total_earnings = 0

    parking_list = []

    for p in parkings:

        bookings = await database.bookings.find({
            "parking_id": str(p["_id"])
        }).to_list(100)

        # ✅ ACTIVE BOOKINGS (count slots)
        active = sum(
            b.get("slots_booked", 1)
            for b in bookings
            if b.get("status") == "active"
        )

        # ✅ EARNINGS (active + completed)
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
            "active_bookings": active,   # ✅ FIXED
            "earnings": earnings         # ✅ FIXED
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
    user=Depends(get_current_user)
):
    # ✅ fetch the parking space owned by the current user
    parking_space = await database.parkings.find_one({"_id": ObjectId(space_id), "owner_id": str(user["_id"])})

    if not parking_space:
        raise HTTPException(status_code=404, detail="Parking space not found")

    # ✅ handle optional image
    image_path = parking_space.get("image")
    if image:
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{image.filename}"
        with open(file_path, "wb") as f:
            f.write(await image.read())
        image_path = file_path

    # ✅ update MongoDB document
    await database.parkings.update_one(
        {"_id": ObjectId(space_id)},
        {"$set": {
            "name": name,
            "city": city,
            "landmark": landmark,
            "address": address,
            "total_slots": slots,
            "price_per_hour": price_per_hour,
            "available_days": days,
            "features": features,
            "image": image_path
        }}
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
            "price_per_hour": updated_parking["price_per_hour"],
            "days": updated_parking.get("available_days", []),
            "features": updated_parking.get("features", []),
            "image_url": updated_parking.get("image")
        }
    }