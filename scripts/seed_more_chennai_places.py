import os
import pymongo
from dotenv import load_dotenv

load_dotenv('d:/ParkMe/Backend/.env')
uri = os.getenv('MONGO_URL')

client = pymongo.MongoClient(uri)
db = client.parkme

# Retrieve an existing owner id to associate these verified listings
sample_parking = db.parkings.find_one({"owner_id": {"$exists": True, "$ne": None}})
owner_id = sample_parking.get("owner_id") if sample_parking else "660000000000000000000001"

new_places = [
    {
        "name": "Nexus Vijaya Mall Parking Deck",
        "city": "Chennai",
        "landmark": "Vadapalani Metro",
        "address": "182, Arcot Rd, Vadapalani, Chennai, Tamil Nadu 600026",
        "lat": 13.0500,
        "lng": 80.2096,
        "price_per_hour": 50,
        "total_slots": 35,
        "available_slots": 28,
        "features": ["CCTV", "Security Guard", "Covered", "EV Charging", "24/7 Access", "Elevator"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Besant Nagar Elliot's Beach Public Lot",
        "city": "Chennai",
        "landmark": "Elliot's Beach Promenade",
        "address": "6th Ave, Besant Nagar, Chennai, Tamil Nadu 600090",
        "lat": 12.9997,
        "lng": 80.2721,
        "price_per_hour": 30,
        "total_slots": 25,
        "available_slots": 19,
        "features": ["CCTV", "Security Guard", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Olympia Tech Park Smart Bay",
        "city": "Chennai",
        "landmark": "Guindy Metro Station",
        "address": "1, SIDCO Industrial Estate, Guindy, Chennai, Tamil Nadu 600032",
        "lat": 13.0118,
        "lng": 80.2078,
        "price_per_hour": 60,
        "total_slots": 40,
        "available_slots": 31,
        "features": ["CCTV", "Security Guard", "Covered", "EV Charging", "Boom Barrier", "FastTag"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "image": "https://images.unsplash.com/photo-1573348722427-f1d6819fdf98?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1573348722427-f1d6819fdf98?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Nungambakkam High Road Automated Deck",
        "city": "Chennai",
        "landmark": "Near Taj Coromandel",
        "address": "37, Mahatma Gandhi Rd, Nungambakkam, Chennai, Tamil Nadu 600034",
        "lat": 13.0604,
        "lng": 80.2428,
        "price_per_hour": 45,
        "total_slots": 20,
        "available_slots": 14,
        "features": ["CCTV", "Covered", "Security Guard", "Automated Lift"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1545459720-aac8509eb02c?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1545459720-aac8509eb02c?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Chennai Egmore Station North MLCP",
        "city": "Chennai",
        "landmark": "Opposite Egmore Railway Station",
        "address": "Gandhi Irwin Rd, Egmore, Chennai, Tamil Nadu 600008",
        "lat": 13.0805,
        "lng": 80.2608,
        "price_per_hour": 35,
        "total_slots": 30,
        "available_slots": 22,
        "features": ["CCTV", "Security Guard", "Covered", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1470224114660-3f6686c562eb?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1470224114660-3f6686c562eb?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Koyambedu CMBT Transit Complex",
        "city": "Chennai",
        "landmark": "Near CMBT Metro Terminal",
        "address": "Koyambedu Roundtana, Chennai, Tamil Nadu 600107",
        "lat": 13.0673,
        "lng": 80.1947,
        "price_per_hour": 40,
        "total_slots": 50,
        "available_slots": 42,
        "features": ["CCTV", "Security Guard", "Covered", "24/7 Access", "Transit Link"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Adyar Shastri Nagar Smart Parking Bay",
        "city": "Chennai",
        "landmark": "Adyar Bus Depot Junction",
        "address": "1st Avenue, Shastri Nagar, Adyar, Chennai, Tamil Nadu 600020",
        "lat": 13.0012,
        "lng": 80.2565,
        "price_per_hour": 35,
        "total_slots": 22,
        "available_slots": 16,
        "features": ["CCTV", "Security Guard", "Covered", "FastTag"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "image": "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    },
    {
        "name": "Tidel Park Tech Zone MLCP",
        "city": "Chennai",
        "landmark": "Tidel Park Junction OMR",
        "address": "Rajiv Gandhi Salai, Taramani, Chennai, Tamil Nadu 600113",
        "lat": 12.9893,
        "lng": 80.2476,
        "price_per_hour": 55,
        "total_slots": 45,
        "available_slots": 37,
        "features": ["CCTV", "Security Guard", "Covered", "EV Charging", "Automated Lift", "24/7 Access"],
        "available_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80",
        "images": ["https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80"],
        "owner_id": owner_id
    }
]

inserted_count = 0
for place in new_places:
    existing = db.parkings.find_one({"name": place["name"]})
    if not existing:
        db.parkings.insert_one(place)
        print(f"Inserted: {place['name']}")
        inserted_count += 1
    else:
        print(f"Already exists: {place['name']}")

print(f"\nDone! Newly inserted: {inserted_count}, Total spaces now: {db.parkings.count_documents({})}")
