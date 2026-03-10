from fastapi import FastAPI
from routes import user_routes
from routes import parking_routes
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

app.include_router(user_routes.router)
app.include_router(parking_routes.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all domains (for testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
