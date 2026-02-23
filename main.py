from fastapi import FastAPI
from routes import user_routes
from routes import parking_routes


app = FastAPI()

app.include_router(user_routes.router)
app.include_router(parking_routes.router)