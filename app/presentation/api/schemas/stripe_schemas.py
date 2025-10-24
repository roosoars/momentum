"""Pydantic schemas for Stripe API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field


class StripeConfigureRequest(BaseModel):
    """Request to configure Stripe API keys."""

    mode: str = Field(..., description="Mode: 'test' or 'production'")
    test_secret_key: Optional[str] = Field(None, description="Stripe test mode secret key")
    test_publishable_key: Optional[str] = Field(None, description="Stripe test mode publishable key")
    prod_secret_key: Optional[str] = Field(None, description="Stripe production mode secret key")
    prod_publishable_key: Optional[str] = Field(None, description="Stripe production mode publishable key")


class StripeCreateSubscriptionRequest(BaseModel):
    """Request to create a subscription."""

    customer_email: str = Field(..., description="Customer email address")
    price_id: str = Field(..., description="Stripe Price ID for the subscription")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID (optional for testing)")
