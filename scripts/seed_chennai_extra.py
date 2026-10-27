import os
import pymongo
from dotenv import load_dotenv

load_dotenv('d:/ParkMe/Backend/.env')
uri = os.getenv('MONGO_URL')

client = pymongo.MongoClient(uri)
db = client.parkme

sample = db.parkings.find_one({"owner_id": {"$exists": True, "$ne": None}})
owner_id = sample.get("owner_id") if sample else "660000000000000000000001"

extra_places = [
    {
        "name": "Phoenix Palladium Multi-Deck Hub",
        "city": "Chennai",
        "landmark": "Near Velachery MRTS",
        "address": "142, Velachery Main Rd, Indira Gandhi Nagar, Velachery, Chennai 600042",
        "lat": 12.9922,
        "lng": 80.2173,
        "latitude": 12.9922,
        "longitude": 80.2173,
        "location": {"type": "Point", "coordinates": [80.2173, 12.9922]},
        "price_per_hour": 50,
        "total_slots": 40,
        "available_slots": 32,
        "features": ["CCTV", "Security Guard", "Covered", "EV Charging", "24/7 Access", "Elevator"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Ampa Skywalk Smart Level Deck",
        "city": "Chennai",
        "landmark": "Aminjikarai Junction",
        "address": "1, Nelson Manickam Rd, Aminjikarai, Chennai, Tamil Nadu 600029",
        "lat": 13.0727,
        "lng": 80.2185,
        "latitude": 13.0727,
        "longitude": 80.2185,
        "location": {"type": "Point", "coordinates": [80.2185, 13.0727]},
        "price_per_hour": 40,
        "total_slots": 30,
        "available_slots": 21,
        "features": ["CCTV", "Covered", "Security Guard", "Boom Barrier"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1573348722427-f1d6819fdf98?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1573348722427-f1d6819fdf98?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Spencer Plaza Central Parking Bay",
        "city": "Chennai",
        "landmark": "Near Thousand Lights Metro",
        "address": "769, Anna Salai, Thousand Lights, Chennai, Tamil Nadu 600002",
        "lat": 13.0617,
        "lng": 80.2612,
        "latitude": 13.0617,
        "longitude": 80.2612,
        "location": {"type": "Point", "coordinates": [80.2612, 13.0617]},
        "price_per_hour": 35,
        "total_slots": 35,
        "available_slots": 24,
        "features": ["CCTV", "Security Guard", "Covered", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Alwarpet TTK Road Reserved MLCP",
        "city": "Chennai",
        "landmark": "Music Academy Junction",
        "address": "TT Krishnamachari Rd, Alwarpet, Chennai, Tamil Nadu 600018",
        "lat": 13.0336,
        "lng": 80.2520,
        "latitude": 13.0336,
        "longitude": 80.2520,
        "location": {"type": "Point", "coordinates": [80.2520, 13.0336]},
        "price_per_hour": 45,
        "total_slots": 25,
        "available_slots": 18,
        "features": ["CCTV", "Covered", "Security Guard", "EV Charging"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1545459720-aac8509eb02c?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1545459720-aac8509eb02c?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Guindy SIDCO Industrial Tech Lot",
        "city": "Chennai",
        "landmark": "Near Guindy Flyover",
        "address": "SIDCO Industrial Estate, Guindy, Chennai, Tamil Nadu 600032",
        "lat": 13.0067,
        "lng": 80.2030,
        "latitude": 13.0067,
        "longitude": 80.2030,
        "location": {"type": "Point", "coordinates": [80.2030, 13.0067]},
        "price_per_hour": 30,
        "total_slots": 30,
        "available_slots": 22,
        "features": ["CCTV", "Security Guard", "24/7 Access", "Heavy Duty"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "EA Chambers Royapettah Smart Bay",
        "city": "Chennai",
        "landmark": "Opposite Express Avenue Gate 2",
        "address": "49, Whites Rd, Royapettah, Chennai, Tamil Nadu 600014",
        "lat": 13.0581,
        "lng": 80.2641,
        "latitude": 13.0581,
        "longitude": 80.2641,
        "location": {"type": "Point", "coordinates": [80.2641, 13.0581]},
        "price_per_hour": 45,
        "total_slots": 28,
        "available_slots": 19,
        "features": ["CCTV", "Covered", "Security Guard", "EV Charging", "FastTag"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    }
]

added = 0
for place in extra_places:
    if not db.parkings.find_one({"name": place["name"]}):
        db.parkings.insert_one(place)
        print(f"Added real place: {place['name']}")
        added += 1

print(f"\nAdded {added} real places. Total spaces now: {db.parkings.count_documents({})}")
