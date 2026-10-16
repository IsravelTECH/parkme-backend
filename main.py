import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import database
from routes import (
    user_routes,
    parking_routes,
    booking_routes,
    admin_routes,
    profile_routes,
)
from routes.stripe_routes import router as stripe_router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure static directories exist
    os.makedirs("static/profile", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)

    # Create 2dsphere Geospatial Index for nearby parking queries
    try:
        await database.parkings.create_index([("location", "2dsphere")])
        print("[OK] 2dsphere Geo index ensured on 'parkings.location'")
    except Exception as e:
        print("[WARN] Could not create geo index on startup:", e)

    yield

app = FastAPI(title="ParkMe API", lifespan=lifespan)

# Setup CORS
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env.strip():
    origins = [orig.strip().rstrip("/") for orig in allowed_origins_env.split(",") if orig.strip()]
else:
    origins = [
        "https://parkme-six.vercel.app",
        "https://effortless-choux-d62f15.netlify.app",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3005",
        "http://127.0.0.1:3005",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

# Always ensure the deployed frontend is permitted
if "https://parkme-six.vercel.app" not in origins:
    origins.append("https://parkme-six.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1)(:[0-9]+)?|https://.*\.vercel\.app|https://.*\.netlify\.app)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Directories
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(user_routes.router)
app.include_router(parking_routes.router)
app.include_router(profile_routes.router)
app.include_router(booking_routes.router)
app.include_router(admin_routes.router)
app.include_router(stripe_router)