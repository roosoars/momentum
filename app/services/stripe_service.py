"""Stripe payment integration service."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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
    SETTING_WEBHOOK_SECRET = "stripe_webhook_secret"

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
        webhook_secret = self._persistence.get_setting(self.SETTING_WEBHOOK_SECRET)

        return {
            "mode": mode,
            "test_configured": bool(test_secret and test_publishable),
            "production_configured": bool(prod_secret and prod_publishable),
            "test_publishable_key": test_publishable if test_publishable else None,
            "production_publishable_key": prod_publishable if prod_publishable else None,
            "connected": self.is_connected(),
            "webhook_configured": bool(webhook_secret),
        }

    def configure(
        self,
        mode: str,
        test_secret_key: Optional[str] = None,
        test_publishable_key: Optional[str] = None,
        prod_secret_key: Optional[str] = None,
        prod_publishable_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
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
        if webhook_secret:
            self._persistence.set_setting(self.SETTING_WEBHOOK_SECRET, webhook_secret.strip())

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

    # ============ PRODUCTS & PRICES ============

    def list_products(self, limit: int = 100, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List Stripe products with their prices."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            params: Dict[str, Any] = {"limit": limit}
            if not include_inactive:
                params["active"] = True

            products = stripe.Product.list(**params)
            result = []
            for product in products.data:
                # Get prices for this product
                prices = stripe.Price.list(product=product.id, active=True if not include_inactive else None)
                result.append({
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "active": product.active,
                    "created": product.created,
                    "prices": [
                        {
                            "id": price.id,
                            "active": price.active,
                            "amount": price.unit_amount,
                            "currency": price.currency,
                            "type": price.type,
                            "recurring": {
                                "interval": price.recurring.get("interval"),
                                "interval_count": price.recurring.get("interval_count"),
                            } if price.recurring else None,
                        }
                        for price in prices.data
                    ],
                })
            return result
        except Exception as e:
            logger.error("Failed to list products: %s", str(e))
            raise ValueError(f"Failed to list products: {str(e)}")

    def create_product(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Stripe product."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            product = stripe.Product.create(
                name=name,
                description=description if description else None,
            )
            return {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "active": product.active,
                "created": product.created,
            }
        except Exception as e:
            logger.error("Failed to create product: %s", str(e))
            raise ValueError(f"Failed to create product: {str(e)}")

    def update_product(
        self,
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a Stripe product."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            params: Dict[str, Any] = {}
            if name is not None:
                params["name"] = name
            if description is not None:
                params["description"] = description
            if active is not None:
                params["active"] = active

            product = stripe.Product.modify(product_id, **params)
            return {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "active": product.active,
            }
        except Exception as e:
            logger.error("Failed to update product: %s", str(e))
            raise ValueError(f"Failed to update product: {str(e)}")

    def delete_product(self, product_id: str) -> None:
        """Delete (archive) a Stripe product."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            stripe.Product.modify(product_id, active=False)
        except Exception as e:
            logger.error("Failed to delete product: %s", str(e))
            raise ValueError(f"Failed to delete product: {str(e)}")

    def create_price(
        self,
        product_id: str,
        amount: int,
        currency: str = "brl",
        recurring_interval: Optional[str] = None,
        recurring_interval_count: int = 1,
    ) -> Dict[str, Any]:
        """Create a new price for a product."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            params: Dict[str, Any] = {
                "product": product_id,
                "unit_amount": amount,
                "currency": currency,
            }

            if recurring_interval:
                params["recurring"] = {
                    "interval": recurring_interval,
                    "interval_count": recurring_interval_count,
                }

            price = stripe.Price.create(**params)
            return {
                "id": price.id,
                "product": price.product,
                "amount": price.unit_amount,
                "currency": price.currency,
                "type": price.type,
                "recurring": {
                    "interval": price.recurring.get("interval"),
                    "interval_count": price.recurring.get("interval_count"),
                } if price.recurring else None,
            }
        except Exception as e:
            logger.error("Failed to create price: %s", str(e))
            raise ValueError(f"Failed to create price: {str(e)}")

    def update_price(self, price_id: str, active: bool) -> Dict[str, Any]:
        """Update a price (mainly for activating/deactivating)."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            price = stripe.Price.modify(price_id, active=active)
            return {
                "id": price.id,
                "active": price.active,
                "amount": price.unit_amount,
                "currency": price.currency,
            }
        except Exception as e:
            logger.error("Failed to update price: %s", str(e))
            raise ValueError(f"Failed to update price: {str(e)}")

    # ============ SUBSCRIPTIONS ============

    def list_subscriptions(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List all subscriptions."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            params: Dict[str, Any] = {"limit": limit, "expand": ["data.customer"]}
            if status:
                params["status"] = status

            subscriptions = stripe.Subscription.list(**params)
            result = []
            for sub in subscriptions.data:
                result.append({
                    "id": sub.id,
                    "customer_id": sub.customer.id if hasattr(sub.customer, "id") else sub.customer,
                    "customer_email": sub.customer.email if hasattr(sub.customer, "email") else None,
                    "status": sub.status,
                    "current_period_start": sub.current_period_start,
                    "current_period_end": sub.current_period_end,
                    "cancel_at_period_end": sub.cancel_at_period_end,
                    "created": sub.created,
                    "items": [
                        {
                            "price_id": item.price.id,
                            "product_id": item.price.product,
                            "amount": item.price.unit_amount,
                            "currency": item.price.currency,
                        }
                        for item in sub.items.data
                    ],
                })
            return result
        except Exception as e:
            logger.error("Failed to list subscriptions: %s", str(e))
            raise ValueError(f"Failed to list subscriptions: {str(e)}")

    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get a specific subscription by ID."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            sub = stripe.Subscription.retrieve(subscription_id, expand=["customer"])
            return {
                "id": sub.id,
                "customer_id": sub.customer.id if hasattr(sub.customer, "id") else sub.customer,
                "customer_email": sub.customer.email if hasattr(sub.customer, "email") else None,
                "status": sub.status,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "created": sub.created,
                "items": [
                    {
                        "price_id": item.price.id,
                        "product_id": item.price.product,
                        "amount": item.price.unit_amount,
                        "currency": item.price.currency,
                    }
                    for item in sub.items.data
                ],
            }
        except Exception as e:
            logger.error("Failed to get subscription: %s", str(e))
            raise ValueError(f"Failed to get subscription: {str(e)}")

    def create_subscription(
        self,
        customer_email: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new subscription."""
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

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel a subscription."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            if at_period_end:
                sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
            else:
                sub = stripe.Subscription.cancel(subscription_id)

            return {
                "id": sub.id,
                "status": sub.status,
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
        except Exception as e:
            logger.error("Failed to cancel subscription: %s", str(e))
            raise ValueError(f"Failed to cancel subscription: {str(e)}")

    # ============ CUSTOMERS ============

    def list_customers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all customers."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            customers = stripe.Customer.list(limit=limit)
            result = []
            for customer in customers.data:
                result.append({
                    "id": customer.id,
                    "email": customer.email,
                    "name": customer.name,
                    "created": customer.created,
                    "balance": customer.balance,
                    "currency": customer.currency,
                })
            return result
        except Exception as e:
            logger.error("Failed to list customers: %s", str(e))
            raise ValueError(f"Failed to list customers: {str(e)}")

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get a specific customer."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created,
                "balance": customer.balance,
                "currency": customer.currency,
                "description": customer.description,
            }
        except Exception as e:
            logger.error("Failed to get customer: %s", str(e))
            raise ValueError(f"Failed to get customer: {str(e)}")

    def get_customer_subscriptions(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all subscriptions for a customer."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            subscriptions = stripe.Subscription.list(customer=customer_id)
            result = []
            for sub in subscriptions.data:
                result.append({
                    "id": sub.id,
                    "status": sub.status,
                    "current_period_start": sub.current_period_start,
                    "current_period_end": sub.current_period_end,
                    "cancel_at_period_end": sub.cancel_at_period_end,
                    "items": [
                        {
                            "price_id": item.price.id,
                            "amount": item.price.unit_amount,
                            "currency": item.price.currency,
                        }
                        for item in sub.items.data
                    ],
                })
            return result
        except Exception as e:
            logger.error("Failed to get customer subscriptions: %s", str(e))
            raise ValueError(f"Failed to get customer subscriptions: {str(e)}")

    def get_customer_invoices(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get invoices for a customer."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
            result = []
            for invoice in invoices.data:
                result.append({
                    "id": invoice.id,
                    "amount_due": invoice.amount_due,
                    "amount_paid": invoice.amount_paid,
                    "currency": invoice.currency,
                    "status": invoice.status,
                    "created": invoice.created,
                    "period_start": invoice.period_start,
                    "period_end": invoice.period_end,
                })
            return result
        except Exception as e:
            logger.error("Failed to get customer invoices: %s", str(e))
            raise ValueError(f"Failed to get customer invoices: {str(e)}")

    # ============ METRICS ============

    def get_metrics(self) -> Dict[str, Any]:
        """Get business metrics from Stripe."""
        if not stripe.api_key:
            raise ValueError("Stripe not configured. Please set API keys first.")

        try:
            # Get all active subscriptions
            active_subs = stripe.Subscription.list(status="active", limit=100)

            # Calculate MRR (Monthly Recurring Revenue)
            mrr = 0
            for sub in active_subs.data:
                for item in sub.items.data:
                    amount = item.price.unit_amount or 0
                    if item.price.recurring:
                        interval = item.price.recurring.get("interval")
                        interval_count = item.price.recurring.get("interval_count", 1)

                        # Convert to monthly
                        if interval == "month":
                            mrr += amount / interval_count
                        elif interval == "year":
                            mrr += amount / (12 * interval_count)

            # Get subscriptions created in the last 30 days
            thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
            recent_subs = stripe.Subscription.list(
                created={"gte": thirty_days_ago},
                limit=100
            )

            # Get canceled subscriptions in the last 30 days
            canceled_subs = stripe.Subscription.list(
                status="canceled",
                created={"gte": thirty_days_ago},
                limit=100
            )

            # Count all statuses
            all_subs = stripe.Subscription.list(limit=100)
            status_counts = {
                "active": 0,
                "trialing": 0,
                "past_due": 0,
                "canceled": 0,
                "incomplete": 0,
            }

            for sub in all_subs.data:
                status = sub.status
                if status in status_counts:
                    status_counts[status] += 1

            # Get total customers
            customers = stripe.Customer.list(limit=1)

            return {
                "mrr": mrr / 100,  # Convert from cents
                "total_subscriptions": active_subs.total_count or len(active_subs.data),
                "new_subscriptions_30d": len(recent_subs.data),
                "canceled_subscriptions_30d": len(canceled_subs.data),
                "churn_rate_30d": (
                    len(canceled_subs.data) / max(len(active_subs.data), 1) * 100
                ) if active_subs.data else 0,
                "total_customers": customers.total_count if hasattr(customers, "total_count") else 0,
                "subscriptions_by_status": status_counts,
            }
        except Exception as e:
            logger.error("Failed to get metrics: %s", str(e))
            raise ValueError(f"Failed to get metrics: {str(e)}")

    # ============ TEST HELPERS ============

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
