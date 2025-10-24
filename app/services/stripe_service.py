"""Stripe payment integration service."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import stripe

from ..domain.ports.persistence import PersistenceGateway

logger = logging.getLogger(__name__)


class StripeService:
    """Manages Stripe API integration for subscriptions and payments."""

    SETTING_TEST_SECRET_KEY = "stripe_test_secret_key"
    SETTING_TEST_PUBLISHABLE_KEY = "stripe_test_publishable_key"
    SETTING_PROD_SECRET_KEY = "stripe_prod_secret_key"
    SETTING_PROD_PUBLISHABLE_KEY = "stripe_prod_publishable_key"
    SETTING_MODE = "stripe_mode"  # "test" or "production"

    def __init__(self, persistence: PersistenceGateway) -> None:
        self._persistence = persistence
        self._configure_stripe()

    def _configure_stripe(self) -> None:
        """Configure Stripe SDK with current API key based on mode."""
        mode = self.get_mode()
        if mode == "production":
            secret_key = self._persistence.get_setting(self.SETTING_PROD_SECRET_KEY)
        else:
            secret_key = self._persistence.get_setting(self.SETTING_TEST_SECRET_KEY)

        if secret_key:
            stripe.api_key = secret_key
        else:
            stripe.api_key = None

    def get_configuration(self) -> Dict[str, Any]:
        """Get current Stripe configuration."""
        mode = self.get_mode()
        test_secret = self._persistence.get_setting(self.SETTING_TEST_SECRET_KEY)
        test_publishable = self._persistence.get_setting(self.SETTING_TEST_PUBLISHABLE_KEY)
        prod_secret = self._persistence.get_setting(self.SETTING_PROD_SECRET_KEY)
        prod_publishable = self._persistence.get_setting(self.SETTING_PROD_PUBLISHABLE_KEY)

        return {
            "mode": mode,
            "test_configured": bool(test_secret and test_publishable),
            "production_configured": bool(prod_secret and prod_publishable),
            "test_publishable_key": test_publishable if test_publishable else None,
            "production_publishable_key": prod_publishable if prod_publishable else None,
            "connected": self.is_connected(),
        }

    def configure(
        self,
        mode: str,
        test_secret_key: Optional[str] = None,
        test_publishable_key: Optional[str] = None,
        prod_secret_key: Optional[str] = None,
        prod_publishable_key: Optional[str] = None,
    ) -> None:
        """Configure Stripe API keys."""
        if mode not in ("test", "production"):
            raise ValueError("Mode must be 'test' or 'production'")

        # Save keys if provided
        if test_secret_key:
            self._persistence.set_setting(self.SETTING_TEST_SECRET_KEY, test_secret_key.strip())
        if test_publishable_key:
            self._persistence.set_setting(self.SETTING_TEST_PUBLISHABLE_KEY, test_publishable_key.strip())
        if prod_secret_key:
            self._persistence.set_setting(self.SETTING_PROD_SECRET_KEY, prod_secret_key.strip())
        if prod_publishable_key:
            self._persistence.set_setting(self.SETTING_PROD_PUBLISHABLE_KEY, prod_publishable_key.strip())

        # Set mode
        self._persistence.set_setting(self.SETTING_MODE, mode)

        # Reconfigure Stripe SDK
        self._configure_stripe()

        logger.info("Stripe configured in %s mode", mode)

    def get_mode(self) -> str:
        """Get current Stripe mode (test or production)."""
        mode = self._persistence.get_setting(self.SETTING_MODE)
        return mode if mode in ("test", "production") else "test"

    def is_connected(self) -> bool:
        """Check if Stripe is properly configured and connected."""
        if not stripe.api_key:
            return False

        try:
            # Try to retrieve account information
            stripe.Account.retrieve()
            return True
        except Exception as e:
            logger.debug("Stripe connection check failed: %s", str(e))
            return False

    def get_account_info(self) -> Dict[str, Any]:
        """Get Stripe account information."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            account = stripe.Account.retrieve()
            return {
                "id": account.id,
                "email": account.email,
                "country": account.country,
                "currency": account.default_currency,
                "business_name": account.business_profile.get("name") if account.business_profile else None,
            }
        except stripe.error.AuthenticationError:
            raise ValueError("Invalid Stripe API key")
        except Exception as e:
            logger.error("Failed to retrieve Stripe account: %s", str(e))
            raise ValueError(f"Failed to retrieve Stripe account: {str(e)}")

    def create_subscription(
        self,
        customer_email: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a test subscription."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            # Create or retrieve customer
            customers = stripe.Customer.list(email=customer_email, limit=1)
            if customers.data:
                customer = customers.data[0]
            else:
                customer = stripe.Customer.create(email=customer_email)

            # Create subscription
            subscription_params: Dict[str, Any] = {
                "customer": customer.id,
                "items": [{"price": price_id}],
                "payment_behavior": "default_incomplete",
                "expand": ["latest_invoice.payment_intent"],
            }

            if payment_method_id:
                subscription_params["default_payment_method"] = payment_method_id

            subscription = stripe.Subscription.create(**subscription_params)

            return {
                "subscription_id": subscription.id,
                "customer_id": customer.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "client_secret": (
                    subscription.latest_invoice.payment_intent.client_secret
                    if hasattr(subscription.latest_invoice, "payment_intent")
                    and subscription.latest_invoice.payment_intent
                    else None
                ),
            }
        except stripe.error.InvalidRequestError as e:
            raise ValueError(f"Invalid request: {str(e)}")
        except stripe.error.AuthenticationError:
            raise ValueError("Invalid Stripe API key")
        except Exception as e:
            logger.error("Failed to create subscription: %s", str(e))
            raise ValueError(f"Failed to create subscription: {str(e)}")

    def list_products(self, limit: int = 10) -> list[Dict[str, Any]]:
        """List available Stripe products."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            products = stripe.Product.list(limit=limit, active=True)
            result = []
            for product in products.data:
                # Get prices for this product
                prices = stripe.Price.list(product=product.id, active=True)
                result.append({
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "prices": [
                        {
                            "id": price.id,
                            "amount": price.unit_amount,
                            "currency": price.currency,
                            "interval": price.recurring.get("interval") if price.recurring else None,
                            "interval_count": price.recurring.get("interval_count") if price.recurring else None,
                        }
                        for price in prices.data
                    ],
                })
            return result
        except Exception as e:
            logger.error("Failed to list products: %s", str(e))
            raise ValueError(f"Failed to list products: {str(e)}")

    def create_test_subscription_for_testing(self) -> Dict[str, Any]:
        """Create a test subscription with dummy data for testing the integration."""
        if self.get_mode() != "test":
            raise ValueError("This endpoint only works in test mode")

        try:
            # Create a test customer
            customer = stripe.Customer.create(
                email="test@momentum.com",
                description="Test customer created by Momentum",
            )

            # List available prices and use the first one
            prices = stripe.Price.list(active=True, limit=1)
            if not prices.data:
                raise ValueError(
                    "No active prices found. Please create a product and price in Stripe Dashboard first."
                )

            price = prices.data[0]

            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price.id}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
            )

            return {
                "success": True,
                "message": "Test subscription created successfully",
                "subscription_id": subscription.id,
                "customer_id": customer.id,
                "customer_email": "test@momentum.com",
                "status": subscription.status,
                "price_id": price.id,
                "amount": price.unit_amount,
                "currency": price.currency,
                "interval": price.recurring.get("interval") if price.recurring else None,
            }
        except stripe.error.InvalidRequestError as e:
            raise ValueError(f"Stripe request error: {str(e)}")
        except Exception as e:
            logger.error("Failed to create test subscription: %s", str(e))
            raise ValueError(f"Failed to create test subscription: {str(e)}")
