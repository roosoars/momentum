"""Pydantic schemas for subscription API endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CreateCheckoutSessionRequest(BaseModel):
    """Request schema for creating a checkout session."""

    price_id: str


class CreateCheckoutSessionResponse(BaseModel):
    """Response schema for creating a checkout session."""

    checkout_url: str


class SubscriptionResponse(BaseModel):
    """Response schema for subscription data."""

    id: int
    stripe_subscription_id: str
    stripe_price_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    is_active: bool


class PlanResponse(BaseModel):
    """Response schema for available plans."""

    product_id: str
    product_name: str
    product_description: Optional[str]
    prices: list["PriceResponse"]


class PriceResponse(BaseModel):
    """Response schema for a price."""

    price_id: str
    amount: int
    currency: str
    interval: Optional[str]
    interval_count: Optional[int]
