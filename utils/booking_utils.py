from datetime import datetime, timezone
from bson import ObjectId
from database import database

async def auto_complete_bookings():
    """
    Finds all active bookings whose scheduled end_time has passed,
    marks them as 'completed', and restores the available slot capacity
    to the corresponding parking facility.
    """
    now = datetime.now(timezone.utc)

    # Find expired active bookings
    expired = await database.bookings.find({
        "status": "active",
        "end_time": {"$lte": now}
    }).to_list(length=200)

    for b in expired:
        # Atomically mark as completed only if currently active
        update_result = await database.bookings.update_one(
            {"_id": b["_id"], "status": "active"},
            {"$set": {"status": "completed"}}
        )

        # Increment slot back only once when status successfully transitioned
        if update_result.modified_count > 0 and b.get("parking_id"):
            try:
                await database.parkings.update_one(
                    {"_id": ObjectId(b["parking_id"])},
                    {"$inc": {"available_slots": 1}}
                )
            except Exception as e:
                print(f"Failed to increment slot for parking {b.get('parking_id')}: {e}")
