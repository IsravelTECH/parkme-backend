from fastapi import APIRouter, Depends
from database import database
from utils.auth import require_owner

router = APIRouter()

@router.get("/admin-dashboard")
async def admin_dashboard(user=Depends(require_owner)):
    
    users_collection = database["users"]
    bookings_collection = database["bookings"]

    total_users = await users_collection.count_documents({})
    total_bookings = await bookings_collection.count_documents({})

    active_bookings = await bookings_collection.count_documents({
        "status": "active"
    })

    cancelled_bookings = await bookings_collection.count_documents({
        "status": "cancelled"
    })

    # 💰 total earnings (FIXED)
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