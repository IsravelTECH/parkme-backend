from pydantic import BaseModel, EmailStr

class User(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str   # owner or seeker

class LoginRequest(BaseModel):
    email: str
    password: str