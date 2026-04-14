from fastapi import APIRouter, Depends
from database import database
from utils.auth import require_owner
from bson import ObjectId

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