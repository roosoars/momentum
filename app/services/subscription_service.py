"""Service for subscription management with Stripe."""

from datetime import datetime
from typing import List, Optional

import stripe

from app.domain.models.subscription import Subscription
from app.infrastructure.repositories.subscription_repository import SubscriptionRepository


class SubscriptionService:
    """Service for managing user subscriptions."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        stripe_secret_key: Optional[str] = None,
    ):
        self.subscription_repository = subscription_repository
        if stripe_secret_key:
            stripe.api_key = stripe_secret_key

    def create_checkout_session(
        self,
        user_id: int,
        user_email: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """
        Create a Stripe checkout session for a subscription.

        Args:
            user_id: User ID
            user_email: User email
            price_id: Stripe price ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels

        Returns:
            Checkout session URL

        Raises:
            stripe.StripeError: If Stripe API call fails
        """
        # Check if user already has an active subscription
        existing_sub = self.subscription_repository.get_by_user_id(user_id)
        if existing_sub and existing_sub.is_active():
            raise ValueError("User already has an active subscription")

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer_email=user_email,
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user_id),
            },
        )

        return session.url

    def handle_checkout_completed(self, session: dict) -> Subscription:
        """
        Handle a completed checkout session webhook event.

        Args:
            session: Stripe checkout session object

        Returns:
            Created Subscription entity
        """
        user_id = int(session["metadata"]["user_id"])
        customer_id = session["customer"]
        subscription_id = session["subscription"]

        # Retrieve full subscription details from Stripe
        stripe_sub = stripe.Subscription.retrieve(subscription_id)

        # Get price ID from first item
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]

        # Create subscription record
        subscription = self.subscription_repository.create(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            stripe_price_id=price_id,
            status=stripe_sub["status"],
            current_period_start=datetime.fromtimestamp(
                stripe_sub["current_period_start"]
            ),
            current_period_end=datetime.fromtimestamp(
                stripe_sub["current_period_end"]
            ),
            cancel_at_period_end=stripe_sub.get("cancel_at_period_end", False),
        )

        return subscription

    def handle_subscription_updated(self, stripe_subscription: dict) -> None:
        """
        Handle a subscription updated webhook event.

        Args:
            stripe_subscription: Stripe subscription object
        """
        subscription_id = stripe_subscription["id"]

        self.subscription_repository.update_status(
            stripe_subscription_id=subscription_id,
            status=stripe_subscription["status"],
            current_period_start=datetime.fromtimestamp(
                stripe_subscription["current_period_start"]
            ),
            current_period_end=datetime.fromtimestamp(
                stripe_subscription["current_period_end"]
            ),
            cancel_at_period_end=stripe_subscription.get(
                "cancel_at_period_end", False
            ),
        )

    def handle_subscription_deleted(self, stripe_subscription: dict) -> None:
        """
        Handle a subscription deleted webhook event.

        Args:
            stripe_subscription: Stripe subscription object
        """
        subscription_id = stripe_subscription["id"]

        self.subscription_repository.update_status(
            stripe_subscription_id=subscription_id,
            status="canceled",
            current_period_start=datetime.fromtimestamp(
                stripe_subscription["current_period_start"]
            ),
            current_period_end=datetime.fromtimestamp(
                stripe_subscription["current_period_end"]
            ),
            cancel_at_period_end=True,
        )

    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """
        Get active subscription for a user.

        Args:
            user_id: User ID

        Returns:
            Subscription if found, None otherwise
        """
        return self.subscription_repository.get_by_user_id(user_id)

    def has_active_subscription(self, user_id: int) -> bool:
        """
        Check if user has an active subscription.

        Args:
            user_id: User ID

        Returns:
            True if user has active subscription
        """
        subscription = self.subscription_repository.get_by_user_id(user_id)
        return subscription is not None and subscription.is_active()

    def cancel_subscription(self, user_id: int) -> bool:
        """
        Cancel a user's subscription at period end.

        Args:
            user_id: User ID

        Returns:
            True if canceled, False if no active subscription

        Raises:
            stripe.StripeError: If Stripe API call fails
        """
        subscription = self.subscription_repository.get_by_user_id(user_id)
        if not subscription or not subscription.is_active():
            return False

        # Cancel at period end via Stripe
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True,
        )

        # Update local record
        self.subscription_repository.update_status(
            stripe_subscription_id=subscription.stripe_subscription_id,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=True,
        )

        return True

    def list_user_subscriptions(self, user_id: int) -> List[Subscription]:
        """
        List all subscriptions for a user.

        Args:
            user_id: User ID

        Returns:
            List of Subscription entities
        """
        return self.subscription_repository.list_by_user_id(user_id)
