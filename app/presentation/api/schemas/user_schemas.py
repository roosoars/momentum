"""Pydantic schemas for user API endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    password: str


class UserRegisterResponse(BaseModel):
    """Response schema for user registration."""

    user_id: int
    email: str
    message: str


class UserLoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class UserLoginResponse(BaseModel):
    """Response schema for user login."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserVerifyEmailRequest(BaseModel):
    """Request schema for email verification."""

    token: str


class UserResendVerificationRequest(BaseModel):
    """Request schema to resend verification email."""

    email: EmailStr


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: int
    email: str
    is_verified: bool
    created_at: datetime


class UserProfileResponse(BaseModel):
    """Response schema for user profile."""

    id: int
    email: str
    is_verified: bool
    has_active_subscription: bool
    created_at: datetime
