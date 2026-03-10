from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

class User(BaseModel): 
    name: str 
    email: EmailStr 
    password: str 
    role: str # owner or seeker
