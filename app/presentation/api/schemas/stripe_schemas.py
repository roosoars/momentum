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
    webhook_secret: Optional[str] = Field(None, description="Stripe webhook signing secret")


class StripeCreateProductRequest(BaseModel):
    """Request to create a product."""

    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")


class StripeUpdateProductRequest(BaseModel):
    """Request to update a product."""

    name: Optional[str] = Field(None, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    active: Optional[bool] = Field(None, description="Whether the product is active")


class StripeCreatePriceRequest(BaseModel):
    """Request to create a price."""

    product_id: str = Field(..., description="Product ID")
    amount: int = Field(..., description="Amount in cents")
    currency: str = Field(default="brl", description="Currency code")
    recurring_interval: Optional[str] = Field(None, description="Recurring interval: month, year, etc.")
    recurring_interval_count: int = Field(default=1, description="Number of intervals between each billing")


class StripeUpdatePriceRequest(BaseModel):
    """Request to update a price."""

    active: bool = Field(..., description="Whether the price is active")


class StripeCreateSubscriptionRequest(BaseModel):
    """Request to create a subscription."""

    customer_email: str = Field(..., description="Customer email address")
    price_id: str = Field(..., description="Stripe Price ID for the subscription")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID (optional for testing)")


class StripeCancelSubscriptionRequest(BaseModel):
    """Request to cancel a subscription."""

    at_period_end: bool = Field(default=True, description="Whether to cancel at the end of the billing period")
