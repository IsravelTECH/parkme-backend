from fastapi import APIRouter, Depends, Query
from database import database
from utils.auth import require_owner
from bson import ObjectId
from bson.errors import InvalidId
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
                "total": {"$sum": "$total_price"}
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
        doc = serialize(u)
        user_id_str = doc["_id"]

        # Enrolled date derivation
        if not doc.get("created_at"):
            try:
                oid = ObjectId(user_id_str)
                doc["created_at"] = oid.generation_time.strftime("%b %d, %Y")
            except Exception:
                doc["created_at"] = "Oct 2026"
        elif isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].strftime("%b %d, %Y")

        # Booking stats
        try:
            user_bookings = await bookings_collection.find({
                "$or": [{"user_id": user_id_str}, {"user_id": ObjectId(user_id_str)}]
            }).to_list(length=100)
            doc["total_bookings"] = len(user_bookings)
            doc["total_spent"] = sum(b.get("total_price", 0) for b in user_bookings)
            doc["recent_vehicle"] = user_bookings[0].get("vehicle_number") if user_bookings else doc.get("vehicle_number", "TN 09 AB 1234")
        except Exception:
            doc["total_bookings"] = 0
            doc["total_spent"] = 0

        users.append(doc)

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

    q = query.strip()
    safe_query = re.escape(q)
    query_lower = q.lower()

    # ================= USERS =================
    users_cursor = users_collection.find({
        "$or": [
            {"name": {"$regex": safe_query, "$options": "i"}},
            {"email": {"$regex": safe_query, "$options": "i"}},
            {"phone": {"$regex": safe_query, "$options": "i"}},
            {"role": {"$regex": safe_query, "$options": "i"}}
        ]
    }, {"password": 0})

    users = await users_cursor.to_list(length=50)
    users_result = []
    for u in users:
        doc = serialize(u)
        uid_str = doc["_id"]
        if not doc.get("created_at"):
            try:
                doc["created_at"] = ObjectId(uid_str).generation_time.strftime("%b %d, %Y")
            except Exception:
                doc["created_at"] = "Oct 2026"
        elif isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].strftime("%b %d, %Y")

        try:
            ub = await bookings_collection.find({
                "$or": [{"user_id": uid_str}, {"user_id": ObjectId(uid_str)}]
            }).to_list(length=50)
            doc["total_bookings"] = len(ub)
            doc["total_spent"] = sum(b.get("total_price", 0) for b in ub)
        except Exception:
            doc["total_bookings"] = 0
            doc["total_spent"] = 0
        users_result.append(doc)

    # ================= SPACES =================
    spaces_cursor = spaces_collection.find({
        "$or": [
            {"name": {"$regex": safe_query, "$options": "i"}},
            {"address": {"$regex": safe_query, "$options": "i"}},
            {"landmark": {"$regex": safe_query, "$options": "i"}},
            {"city": {"$regex": safe_query, "$options": "i"}}
        ]
    })
    spaces = await spaces_cursor.to_list(length=50)
    spaces_result = [serialize(s) for s in spaces]

    # ================= BOOKINGS =================
    bookings_cursor = bookings_collection.find()
    bookings = await bookings_cursor.to_list(length=200)

    bookings_result = []
    for b in bookings:
        b_doc = serialize(b)
        bid = b_doc["_id"]
        v_num = str(b.get("vehicle_number") or "").lower()
        p_name = str(b.get("parking_name") or "").lower()
        status = str(b.get("status") or "").lower()
        u_email = str(b.get("user_email") or "").lower()
        u_name = str(b.get("user_name") or "").lower()

        is_match = False
        if query_lower in bid.lower():
            is_match = True
        elif query_lower in v_num:
            is_match = True
        elif query_lower in p_name:
            is_match = True
        elif query_lower in status:
            is_match = True
        elif query_lower in u_email or query_lower in u_name:
            is_match = True

        if is_match:
            bookings_result.append(b_doc)

    return {
        "users": users_result,
        "spaces": spaces_result,
        "bookings": bookings_result
    }
