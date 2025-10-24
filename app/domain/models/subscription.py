"""Subscription domain model linking users to Stripe subscriptions."""

from datetime import datetime
from typing import Optional


class Subscription:
    """
    Subscription entity representing a user's Stripe subscription.

    Attributes:
        id: Unique identifier
        user_id: Reference to User
        stripe_customer_id: Stripe customer ID
        stripe_subscription_id: Stripe subscription ID
        stripe_price_id: Stripe price ID
        status: Subscription status (active, canceled, past_due, etc.)
        current_period_start: Start of current billing period
        current_period_end: End of current billing period
        cancel_at_period_end: Whether subscription will cancel at period end
        created_at: Subscription creation timestamp
        updated_at: Last update timestamp
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        stripe_price_id: str,
        status: str,
        current_period_start: datetime,
        current_period_end: datetime,
        cancel_at_period_end: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id
        self.stripe_price_id = stripe_price_id
        self.status = status
        self.current_period_start = current_period_start
        self.current_period_end = current_period_end
        self.cancel_at_period_end = cancel_at_period_end
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status in ("active", "trialing")

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user_id={self.user_id} status={self.status}>"
