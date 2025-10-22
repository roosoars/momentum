from pydantic import BaseModel, EmailStr


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminRegisterRequest(BaseModel):
    email: EmailStr
    password: str
