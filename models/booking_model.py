from pydantic import BaseModel

class Booking(BaseModel):
    parking_id: str
    hours: int