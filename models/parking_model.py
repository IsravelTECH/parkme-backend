from pydantic import BaseModel
from typing import List, Optional

class Parking(BaseModel):
    location: str
    price_per_hour: float
    total_slots: int

class ParkingCreate(BaseModel):
    name: str
    city: str
    landmark: str
    address: str

    lat: float
    lng: float

    price_per_hour: int
    total_slots: int
    available_slots: int

    features: List[str]
    available_days: List[str]

    image: Optional[str] = None

