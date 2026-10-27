import re

with open(r'd:\ParkMe\Backend\routes\admin_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace get_all_users
old_users = """@router.get("/admin/users")
async def get_all_users(user=Depends(require_owner)):

    users_cursor = users_collection.find({}, {"password": 0})
    users = []

    async for u in users_cursor:
        users.append(serialize(u))

    return {"users": users}"""

new_users = """@router.get("/admin/users")
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

    return {"users": users}"""

# Find global-search
old_search_start = content.find('@router.get("/admin/global-search")')
if old_search_start == -1:
    raise ValueError("global-search not found")

new_search = """@router.get("/admin/global-search")
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
"""

# Normalize CRLF
content = content.replace(old_users.replace('\n', '\r\n'), new_users.replace('\n', '\r\n'))
if new_users.replace('\n', '\r\n') not in content:
    content = content.replace(old_users, new_users)

old_search_start = content.find('@router.get("/admin/global-search")')
content = content[:old_search_start] + new_search.replace('\n', '\r\n')

with open(r'd:\ParkMe\Backend\routes\admin_routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("admin_routes.py successfully updated!")
