import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('d:/ParkMe/Backend/.env')
MONGO_URL = os.getenv('MONGO_URL')

REAL_PARKING_PLACES = [
    {
        "name": "Express Avenue Multi-Level Parking",
        "city": "Chennai",
        "landmark": "Express Avenue Mall / Whites Road",
        "address": "2, Club House Road, Royapettah, Chennai, Tamil Nadu 600002",
        "location": {"type": "Point", "coordinates": [80.2606, 13.0587]},
        "price_per_hour": 50.0,
        "total_slots": 45,
        "available_slots": 22,
        "features": ["CCTV", "Covered", "EV Charging", "Security Guard", "Valet", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80",
        "owner_id": "699c9359181a64e2bef47e07",
        "added_by": {"name": "Isravel", "email": "isravel@gmail.com"}
    },
    {
        "name": "Phoenix MarketCity Underground Bay",
        "city": "Chennai",
        "landmark": "Phoenix MarketCity / Velachery Bypass",
        "address": "142, Velachery Main Road, Indira Gandhi Nagar, Velachery, Chennai, Tamil Nadu 600042",
        "location": {"type": "Point", "coordinates": [80.2166, 12.9915]},
        "price_per_hour": 60.0,
        "total_slots": 60,
        "available_slots": 34,
        "features": ["CCTV", "Covered", "EV Charging", "Security Guard", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80",
        "owner_id": "699c9359181a64e2bef47e07",
        "added_by": {"name": "Isravel", "email": "isravel@gmail.com"}
    },
    {
        "name": "Chennai Airport MLCP Terminal 2",
        "city": "Chennai",
        "landmark": "Chennai International Airport Terminal 2",
        "address": "Airport Terminal Road, Meenambakkam, Chennai, Tamil Nadu 600027",
        "location": {"type": "Point", "coordinates": [80.1709, 12.9941]},
        "price_per_hour": 80.0,
        "total_slots": 80,
        "available_slots": 48,
        "features": ["CCTV", "Covered", "EV Charging", "Security Guard", "24/7 Access", "Valet"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1573348722427-f1d6819fdf98?auto=format&fit=crop&w=800&q=80",
        "owner_id": "699c9359181a64e2bef47e07",
        "added_by": {"name": "Isravel", "email": "isravel@gmail.com"}
    },
    {
        "name": "Marina Beach Promenade Parking Bay",
        "city": "Chennai",
        "landmark": "Marina Beach Light House / Kamarajar Salai",
        "address": "Kamarajar Salai, Triplicane, Chennai, Tamil Nadu 600005",
        "location": {"type": "Point", "coordinates": [80.2785, 13.0499]},
        "price_per_hour": 30.0,
        "total_slots": 30,
        "available_slots": 16,
        "features": ["CCTV", "Security Guard", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=800&q=80",
        "owner_id": "699c9359181a64e2bef47e07",
        "added_by": {"name": "Isravel", "email": "isravel@gmail.com"}
    },
    {
        "name": "Pondy Bazaar Smart MLCP Hub",
        "city": "Chennai",
        "landmark": "Pondy Bazaar Pedestrian Plaza",
        "address": "Sir Thyagaraya Road, T. Nagar, Chennai, Tamil Nadu 600017",
        "location": {"type": "Point", "coordinates": [80.2337, 13.0418]},
        "price_per_hour": 40.0,
        "total_slots": 40,
        "available_slots": 21,
        "features": ["CCTV", "Covered", "EV Charging", "Security Guard"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1621929747188-0b4dc28498d2?auto=format&fit=crop&w=800&q=80",
        "owner_id": "699c9359181a64e2bef47e07",
        "added_by": {"name": "Isravel", "email": "isravel@gmail.com"}
    },
    {
        "name": "VR Chennai SkyDeck Smart Parking",
        "city": "Chennai",
        "landmark": "VR Chennai / Thirumangalam Metro",
        "address": "100 Feet Road, Thirumangalam, Anna Nagar, Chennai, Tamil Nadu 600040",
        "location": {"type": "Point", "coordinates": [80.1983, 13.0844]},
        "price_per_hour": 50.0,
        "total_slots": 50,
        "available_slots": 32,
        "features": ["CCTV", "Covered", "EV Charging", "Security Guard", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1545459720-aac8509eb02c?auto=format&fit=crop&w=800&q=80",
        "owner_id": "699c9359181a64e2bef47e07",
        "added_by": {"name": "Isravel", "email": "isravel@gmail.com"}
    },
    {
        "name": "OMR Cyber Vale Tech Hub Parking",
        "city": "Chennai",
        "landmark": "Sholinganallur Junction / OMR IT Corridor",
        "address": "Rajiv Gandhi Salai, Sholinganallur, Chennai, Tamil Nadu 600119",
        "location": {"type": "Point", "coordinates": [80.2279, 12.9010]},
        "price_per_hour": 35.0,
        "total_slots": 70,
        "available_slots": 45,
        "features": ["CCTV", "Covered", "EV Charging", "Security Guard", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1470224114660-3f6686c562eb?auto=format&fit=crop&w=800&q=80",
        "owner_id": "699c9359181a64e2bef47e07",
        "added_by": {"name": "Isravel", "email": "isravel@gmail.com"}
    },
    {
        "name": "Chennai Central Multi-Modal Transit Deck",
        "city": "Chennai",
        "landmark": "Dr. MGR Central Railway Station / Metro",
        "address": "Kannappar Thidal, Periyamet, Chennai, Tamil Nadu 600003",
        "location": {"type": "Point", "coordinates": [80.2755, 13.0827]},
        "price_per_hour": 45.0,
        "total_slots": 55,
        "available_slots": 26,
        "features": ["CCTV", "Covered", "Security Guard", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80",
        "owner_id": "699c9359181a64e2bef47e07",
        "added_by": {"name": "Isravel", "email": "isravel@gmail.com"}
    }
]

async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client['parkme']
    collection = db['parkings']

    now_iso = datetime.now(timezone.utc).isoformat()
    inserted_count = 0
    updated_count = 0

    for place in REAL_PARKING_PLACES:
        place['created_at'] = now_iso
        # Check if already exists by name
        existing = await collection.find_one({"name": place["name"]})
        if existing:
            await collection.update_one({"_id": existing["_id"]}, {"$set": place})
            updated_count += 1
            print(f"[UPDATED] {place['name']}")
        else:
            await collection.insert_one(place)
            inserted_count += 1
            print(f"[INSERTED] {place['name']}")

    total = await collection.count_documents({})
    print(f"\n[DONE] Successfully seeded real places! Inserted: {inserted_count}, Updated: {updated_count}. Total parkings in DB: {total}")

if __name__ == "__main__":
    asyncio.run(seed())
