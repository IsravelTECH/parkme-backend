from fastapi import FastAPI
from routes.stripe_routes import router as stripe_router
from routes import user_routes
from routes import parking_routes
from routes import booking_routes
from routes import admin_routes
from fastapi.middleware.cors import CORSMiddleware
from routes import profile_routes
from database import database
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
# ✅ create folders before mounting
os.makedirs("static/profile", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
@app.on_event("startup")
async def startup_db():
    # ✅ Create Geo Index
    await database.parkings.create_index([("location", "2dsphere")])
    print("✅ Geo index created")

app.include_router(user_routes.router)
app.include_router(parking_routes.router)
app.include_router(profile_routes.router)
app.include_router(booking_routes.router)
app.include_router(admin_routes.router) 
app.include_router(stripe_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all domains (for testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")