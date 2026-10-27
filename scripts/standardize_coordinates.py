import os
import pymongo
from dotenv import load_dotenv

load_dotenv('d:/ParkMe/Backend/.env')
db = pymongo.MongoClient(os.getenv('MONGO_URL')).parkme

updated = 0
for p in db.parkings.find():
    lat = None
    lng = None
    if p.get('location') and isinstance(p['location'], dict) and 'coordinates' in p['location']:
        coords = p['location']['coordinates']
        if len(coords) >= 2:
            lng = float(coords[0])
            lat = float(coords[1])
    elif p.get('lat') is not None and p.get('lng') is not None:
        lat = float(p['lat'])
        lng = float(p['lng'])
    elif p.get('latitude') is not None and p.get('longitude') is not None:
        lat = float(p['latitude'])
        lng = float(p['longitude'])
    
    if lat is not None and lng is not None:
        db.parkings.update_one(
            {'_id': p['_id']},
            {'$set': {
                'lat': lat,
                'lng': lng,
                'latitude': lat,
                'longitude': lng,
                'location': {'type': 'Point', 'coordinates': [lng, lat]}
            }}
        )
        updated += 1
        print(f"Updated: {p.get('name')} -> lat={lat}, lng={lng}")

print(f"\nSuccessfully standardized {updated} parking records.")
