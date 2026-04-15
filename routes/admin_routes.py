from fastapi import APIRouter, Depends , Query
from database import database
from utils.auth import require_owner
from bson import ObjectId
from datetime import datetime
import re

router = APIRouter()

# =========================
# COLLECTIONS
# =========================
users_collection = database["users"]
bookings_collection = database["bookings"]
spaces_collection = database["parkings"]
reviews_collection = database["reviews"]


# =========================
# HELPER: CONVERT OBJECTID
# =========================
def serialize(doc):
    doc["_id"] = str(doc["_id"])
    return doc


# =========================
# ✅ DASHBOARD
# =========================
@router.get("/admin-dashboard")
async def admin_dashboard(user=Depends(require_owner)):

    total_users = await users_collection.count_documents({})
    total_bookings = await bookings_collection.count_documents({})

    active_bookings = await bookings_collection.count_documents({
        "status": "active"
    })

    cancelled_bookings = await bookings_collection.count_documents({
        "status": "cancelled"
    })

    # 💰 Earnings (only completed bookings)
    pipeline = [
        {"$match": {"status": "completed"}},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$amount"}
            }
        }
    ]

    cursor = bookings_collection.aggregate(pipeline)
    earnings_result = await cursor.to_list(length=1)

    total_earnings = earnings_result[0]["total"] if earnings_result else 0

    return {
        "total_users": total_users,
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "cancelled_bookings": cancelled_bookings,
        "total_earnings": total_earnings
    }


# =========================
# ✅ ALL USERS
# =========================
@router.get("/admin/users")
async def get_all_users(user=Depends(require_owner)):

    users_cursor = users_collection.find({}, {"password": 0})
    users = []

    async for u in users_cursor:
        users.append(serialize(u))

    return {"users": users}


# =========================
# ✅ RECENT USERS (LATEST CREATED)
# =========================
@router.get("/admin/recent-users")
async def get_recent_users(user=Depends(require_owner)):

    users_cursor = users_collection.find(
        {},
        {"password": 0}
    ).sort("created_at", -1).limit(5)

    users = []

    async for u in users_cursor:
        users.append(serialize(u))

    return {"recent_users": users}


# =========================
# ✅ BOOKINGS
# =========================
@router.get("/admin/bookings")
async def get_bookings(user=Depends(require_owner)):

    bookings_cursor = bookings_collection.find()
    bookings = []

    async for b in bookings_cursor:
        bookings.append(serialize(b))

    return {"bookings": bookings}


# =========================
# ✅ PARKING SPACES
# =========================
@router.get("/admin/spaces")
async def get_spaces(user=Depends(require_owner)):

    spaces_cursor = spaces_collection.find()
    spaces = []

    async for s in spaces_cursor:
        spaces.append(serialize(s))

    return {"spaces": spaces}


# =========================
# ✅ REVIEWS
# =========================
@router.get("/admin/reviews")
async def get_reviews(user=Depends(require_owner)):

    reviews_cursor = reviews_collection.find()
    reviews = []

    async for r in reviews_cursor:
        reviews.append(serialize(r))

    return {"reviews": reviews}


@router.get("/admin/user-growth")
async def user_growth():
    pipeline = [
        {
            "$match": {
                "created_at": {"$ne": None}   # ✅ filter invalid dates
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"}
                },
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {
                "_id.month": {"$ne": None}   # ✅ extra safety
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]

    data = await database.users.aggregate(pipeline).to_list(100)

    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    return {
        "growth": [
            {
                "month": months[item["_id"]["month"] - 1],
                "count": item["count"]
            }
            for item in data
            if item["_id"]["month"] is not None   # ✅ final safety
        ]
    }

@router.get("/admin/review-stats")
async def review_stats():
    pipeline = [
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"}
                },
                "positive": {
                    "$sum": {
                        "$cond": [{"$gte": ["$rating", 4]}, 1, 0]
                    }
                },
                "negative": {
                    "$sum": {
                        "$cond": [{"$lt": ["$rating", 4]}, 1, 0]
                    }
                }
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]

    data = await database.reviews.aggregate(pipeline).to_list(100)

    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    return {
        "monthly": [
            {
                "month": months[item["_id"]["month"] - 1],
                "positive": item["positive"],
                "negative": item["negative"]
            }
            for item in data
        ]
    }
@router.get("/admin/global-search")
async def global_search(query: str = Query(...), user=Depends(require_owner)):

    # ================= USERS =================
    users_cursor = users_collection.find({
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"email": {"$regex": query, "$options": "i"}}
        ]
    }, {"password": 0})

    users = await users_cursor.to_list(length=50)

    users_result = [
        {
            "id": str(u["_id"]),
            "name": u.get("name"),
            "email": u.get("email"),
            "role": u.get("role")
        }
        for u in users
    ]

    # ================= SPACES =================
    spaces_cursor = spaces_collection.find({
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"address": {"$regex": query, "$options": "i"}}
        ]
    })

    spaces = await spaces_cursor.to_list(length=50)

    spaces_result = [
        {
            "id": str(s["_id"]),
            "name": s.get("name"),
            "address": s.get("address"),
            "price_per_hour": s.get("price_per_hour"),
            "total_slots": s.get("total_slots"),
            "available_slots": s.get("available_slots")
        }
        for s in spaces
    ]

    # ================= BOOKINGS =================
    bookings_cursor = bookings_collection.find()
    bookings = await bookings_cursor.to_list(length=100)

    bookings_result = []

    # 🔥 extract digits (e.g., 0902 from "Order #0902")
    match = re.search(r'\d+', query)
    search_digits = match.group() if match else ""

    for b in bookings:

        booking_id_str = str(b["_id"])
        query_lower = query.lower()

        # ================= MATCH LOGIC =================
        is_match = False

        if search_digits and booking_id_str.endswith(search_digits):
            is_match = True

        if query_lower in booking_id_str.lower():
            is_match = True

        if query_lower in (b.get("status") or "").lower():
            is_match = True

        if not is_match:
            continue

        # ================= FETCH USER =================
        user_data = None

        if b.get("user_id"):
            try:
                user_id = b["user_id"]

                # ✅ handle both ObjectId and string
                if isinstance(user_id, str):
                    user_id = ObjectId(user_id)

                user_doc = await users_collection.find_one({"_id": user_id})

                if user_doc:
                    user_data = {
                        "name": user_doc.get("name"),
                        "email": user_doc.get("email")
                    }

            except InvalidId:
                print("❌ Invalid user_id:", b.get("user_id"))
            except Exception as e:
                print("❌ User fetch error:", e)

        # ================= APPEND RESULT =================
        bookings_result.append({
            "id": booking_id_str,
            "short_id": booking_id_str[-4:],  # UI friendly
            "hours": b.get("hours"),
            "status": b.get("status"),
            "total_price": b.get("total_price"),
            "user": user_data
        })

    # ================= FINAL RESPONSE =================
    return {
        "users": users_result,
        "spaces": spaces_result,
        "bookings": bookings_result
    }