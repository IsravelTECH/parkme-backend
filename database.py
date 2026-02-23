import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()   # 🔥 THIS IS IMPORTANT

client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
database = client[os.getenv("DATABASE_NAME")]
