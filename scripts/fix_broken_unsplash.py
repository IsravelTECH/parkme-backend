import os
from pymongo import MongoClient

uri = 'mongodb+srv://israveltech:israveltech@cluster0.hd3ty4r.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(uri)
db = client.parkme

old_url = 'https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80'
new_url = 'https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=800&q=80'

res1 = db.parkings.update_many({'image': old_url}, {'$set': {'image': new_url}})
res2 = db.parkings.update_many({'images': old_url}, {'$set': {'images.$': new_url}})

print(f'Updated image: {res1.modified_count}, images: {res2.modified_count}')
