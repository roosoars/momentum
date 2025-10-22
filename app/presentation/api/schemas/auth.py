from pydantic import BaseModel


class PhonePayload(BaseModel):
    phone: str


class CodePayload(BaseModel):
    code: str


class PasswordPayload(BaseModel):
    password: str
