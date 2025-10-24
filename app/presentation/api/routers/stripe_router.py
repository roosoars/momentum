"""Stripe payment integration API endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ....domain.models import User
from ....services.stripe_service import StripeService
from ....core.dependencies import get_stripe_service
from ...api.dependencies import require_admin_user
from ...api.schemas.stripe_schemas import (
    StripeCancelSubscriptionRequest,
    StripeConfigureRequest,
    StripeCreatePriceRequest,
    StripeCreateProductRequest,
    StripeCreateSubscriptionRequest,
    StripeUpdatePriceRequest,
    StripeUpdateProductRequest,
)

router = APIRouter(prefix="/api/stripe", tags=["Stripe Payments"])


# ============ CONFIGURATION ============

@router.get("/config")
async def get_stripe_config(
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Get current Stripe configuration."""
    return stripe_service.get_configuration()


@router.post("/config")
async def configure_stripe(
    payload: StripeConfigureRequest,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Configure Stripe API keys and mode."""
    try:
        stripe_service.configure(
            mode=payload.mode,
            test_secret_key=payload.test_secret_key,
            test_publishable_key=payload.test_publishable_key,
            prod_secret_key=payload.prod_secret_key,
            prod_publishable_key=payload.prod_publishable_key,
            webhook_secret=payload.webhook_secret,
        )
        return {
            "message": "Stripe configured successfully",
            "config": stripe_service.get_configuration(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/account")
async def get_stripe_account(
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Get Stripe account information."""
    try:
        return stripe_service.get_account_info()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ============ PRODUCTS ============

@router.get("/products")
async def list_stripe_products(
    include_inactive: bool = False,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """List Stripe products and prices."""
    try:
        products = stripe_service.list_products(include_inactive=include_inactive)
        return {"items": products, "count": len(products)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: StripeCreateProductRequest,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Create a new Stripe product."""
    try:
        result = stripe_service.create_product(
            name=payload.name,
            description=payload.description,
        )
        return {"message": "Product created successfully", "product": result}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    payload: StripeUpdateProductRequest,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Update a Stripe product."""
    try:
        result = stripe_service.update_product(
            product_id=product_id,
            name=payload.name,
            description=payload.description,
            active=payload.active,
        )
        return {"message": "Product updated successfully", "product": result}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> None:
    """Delete (archive) a Stripe product."""
    try:
        stripe_service.delete_product(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ============ PRICES ============

@router.post("/prices", status_code=status.HTTP_201_CREATED)
async def create_price(
    payload: StripeCreatePriceRequest,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Create a new price for a product."""
    try:
        result = stripe_service.create_price(
            product_id=payload.product_id,
            amount=payload.amount,
            currency=payload.currency,
            recurring_interval=payload.recurring_interval,
            recurring_interval_count=payload.recurring_interval_count,
        )
        return {"message": "Price created successfully", "price": result}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/prices/{price_id}")
async def update_price(
    price_id: str,
    payload: StripeUpdatePriceRequest,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Update a price (activate/deactivate)."""
    try:
        result = stripe_service.update_price(price_id=price_id, active=payload.active)
        return {"message": "Price updated successfully", "price": result}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ============ SUBSCRIPTIONS ============

@router.get("/subscriptions")
async def list_subscriptions(
    status_filter: str = None,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """List all subscriptions."""
    try:
        subscriptions = stripe_service.list_subscriptions(status=status_filter)
        return {"items": subscriptions, "count": len(subscriptions)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(
    subscription_id: str,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Get a specific subscription."""
    try:
        return stripe_service.get_subscription(subscription_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: StripeCreateSubscriptionRequest,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Create a new subscription."""
    try:
        result = stripe_service.create_subscription(
            customer_email=payload.customer_email,
            price_id=payload.price_id,
            payment_method_id=payload.payment_method_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/subscriptions/{subscription_id}")
async def cancel_subscription(
    subscription_id: str,
    payload: StripeCancelSubscriptionRequest,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Cancel a subscription."""
    try:
        result = stripe_service.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=payload.at_period_end,
        )
        return {"message": "Subscription canceled successfully", "subscription": result}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ============ CUSTOMERS ============

@router.get("/customers")
async def list_customers(
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """List all customers."""
    try:
        customers = stripe_service.list_customers()
        return {"items": customers, "count": len(customers)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Get a specific customer."""
    try:
        return stripe_service.get_customer(customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/customers/{customer_id}/subscriptions")
async def get_customer_subscriptions(
    customer_id: str,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Get all subscriptions for a customer."""
    try:
        subscriptions = stripe_service.get_customer_subscriptions(customer_id)
        return {"items": subscriptions, "count": len(subscriptions)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/customers/{customer_id}/invoices")
async def get_customer_invoices(
    customer_id: str,
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Get invoices for a customer."""
    try:
        invoices = stripe_service.get_customer_invoices(customer_id)
        return {"items": invoices, "count": len(invoices)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ============ METRICS ============

@router.get("/metrics")
async def get_metrics(
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Get business metrics from Stripe."""
    try:
        return stripe_service.get_metrics()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ============ TEST HELPERS ============

@router.post("/test-subscription")
async def create_test_subscription(
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """Create a test subscription with dummy data (test mode only)."""
    try:
        result = stripe_service.create_test_subscription_for_testing()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ============ WEBHOOK ============

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, str]:
    """Handle Stripe webhook events."""
    # This endpoint doesn't require auth - Stripe signs the requests
    # We'll implement webhook verification in the future
    # For now, just return accepted
    return {"status": "received"}
