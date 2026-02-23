from pydantic import BaseModel

class Parking(BaseModel):
    location: str
    price_per_hour: float
    total_slots: int