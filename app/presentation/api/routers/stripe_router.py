"""Stripe payment integration API endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from ....domain.models import User
from ....services.stripe_service import StripeService
from ....core.dependencies import get_stripe_service
from ...api.dependencies import require_admin_user
from ...api.schemas.stripe_schemas import StripeConfigureRequest, StripeCreateSubscriptionRequest

router = APIRouter(prefix="/api/stripe", tags=["Stripe Payments"])


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


@router.get("/products")
async def list_stripe_products(
    _: User = Depends(require_admin_user),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> Dict[str, Any]:
    """List available Stripe products and prices."""
    try:
        products = stripe_service.list_products()
        return {"items": products, "count": len(products)}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/subscription")
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
