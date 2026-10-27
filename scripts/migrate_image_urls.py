import os
import pymongo
from dotenv import load_dotenv

load_dotenv('d:/ParkMe/Backend/.env')
uri = os.getenv('MONGO_URL')

client = pymongo.MongoClient(uri)
db = client.parkme

image_map = {
    'uploads/john-matychuk-yvfp5YHWGsc-unsplash.jpg': 'https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80',
    'uploads/mak-flex-MVGeKI3wZXw-unsplash.jpg': 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80',
    'uploads/michael-fousert-CrU3lUW2jRk-unsplash.jpg': 'https://images.unsplash.com/photo-1573348722427-f1d6819fdf98?auto=format&fit=crop&w=800&q=80',
    'uploads/car park.webp': 'https://images.unsplash.com/photo-1621929747188-0b4dc28498d2?auto=format&fit=crop&w=800&q=80',
    'uploads/bri-tucker-TrvLsDu4sHk-unsplash.jpg': 'https://images.unsplash.com/photo-1545459720-aac8509eb02c?auto=format&fit=crop&w=800&q=80',
    'uploads/sven-mieke-lOgR82HSQKM-unsplash.jpg': 'https://images.unsplash.com/photo-1470224114660-3f6686c562eb?auto=format&fit=crop&w=800&q=80',
    'uploads/Isravel-ID-Card.jpeg': 'https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80'
}

default_fallback = 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80'

updated_count = 0
for parking in db.parkings.find():
    img = parking.get('image')
    if img and (img.startswith('uploads/') or 'onrender.com/uploads' in img):
        new_url = image_map.get(img, default_fallback)
        db.parkings.update_one(
            {'_id': parking['_id']},
            {'$set': {'image': new_url, 'images': [new_url]}}
        )
        print(f"Updated {parking['_id']} ({parking.get('name')}) -> {new_url}")
        updated_count += 1

print(f"\nMigration complete. Total updated: {updated_count}")
