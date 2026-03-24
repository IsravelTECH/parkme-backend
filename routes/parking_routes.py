from fastapi import APIRouter, Depends , Query , Form , UploadFile , File 
from pytest import Session 
from routes.profile_routes import auto_complete_bookings
from models.parking_model import Parking , ParkingCreate
from database import database
from auth import require_role 
from datetime import datetime, timedelta, timezone
from models.booking_model import Booking
from bson import ObjectId
from fastapi import HTTPException
from utils.auth import get_current_user
import os
from typing import List, Optional 



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
async def book_slot(data: dict, current_user = Depends(get_current_user)):

    user_id = str(current_user["_id"])
    parking_id = data.get("parking_id")
    hours = data.get("hours")

    # ✅ get parking details
    parking = await database.parkings.find_one({"_id": ObjectId(parking_id)})

    if not parking:
        return {"error": "Parking not found"}

    if parking.get("available_slots", 0) <= 0:
        return {"error": "No slots available"}

    owner_id = parking.get("owner_id")
    price_per_hour = parking.get("price_per_hour", 0)

    total_price = hours * price_per_hour

    # ✅ CREATE BOOKING (FIXED)
    booking = {
    "parking_id": parking_id,
    "user_id": user_id,
    "owner_id": owner_id,
    "hours": hours,
    "total_price": total_price,
    "status": "active",
    "booking_time": datetime.now(timezone.utc),

    # ✅ ADD THIS
    "end_time": datetime.now(timezone.utc) + timedelta(hours=hours)
}

    await database.bookings.insert_one(booking)

    # ✅ reduce available slots
    await database.parkings.update_one(
        {"_id": ObjectId(parking_id)},
        {"$inc": {"available_slots": -1}}
    )

    return {"message": "Booking successful"}

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

    # SEARCH FILTER
    if search:
        pipeline.append({
            "$match": {
                "$or": [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"address": {"$regex": search, "$options": "i"}}
                ]
            }
        })

    pipeline.append({"$sort": {"distance": 1}})

    results = await database.parkings.aggregate(pipeline).to_list(100)

    response = []
    for r in results:
        response.append({
            "id": str(r["_id"]),
            "name": r.get("name"),
            "address": r.get("address"),

            "lat": r["location"]["coordinates"][1],
            "lng": r["location"]["coordinates"][0],

            "price_per_hour": r.get("price_per_hour"),
            "distance": round(r.get("distance", 0)),

            "available_slots": r.get("available_slots"),
            "image": r.get("image"),

            # ✅ NEW
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