"""API router for user subscription management."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import (
    get_stripe_service,
    get_subscription_service,
)
from app.domain.models.user import User
from app.presentation.api.routers.user_router import require_verified_user
from app.presentation.api.schemas.subscription_schemas import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    PlanResponse,
    PriceResponse,
    SubscriptionResponse,
)
from app.services.stripe_service import StripeService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/users/subscription", tags=["user-subscription"])


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(
    stripe_service: StripeService = Depends(get_stripe_service),
) -> List[PlanResponse]:
    """Get available subscription plans."""
    try:
        # Get all products with prices from Stripe
        products_data = stripe_service.list_products()
        products = products_data.get("items", [])

        plans = []
        for product in products:
            if not product.get("active", False):
                continue

            prices = []
            for price in product.get("prices", []):
                if not price.get("active", False):
                    continue

                recurring = price.get("recurring")
                prices.append(
                    PriceResponse(
                        price_id=price["id"],
                        amount=price.get("amount") or 0,
                        currency=price.get("currency", "brl"),
                        interval=recurring.get("interval") if recurring else None,
                        interval_count=recurring.get("interval_count") if recurring else None,
                    )
                )

            if prices:  # Only include products with active prices
                plans.append(
                    PlanResponse(
                        product_id=product["id"],
                        product_name=product["name"],
                        product_description=product.get("description"),
                        prices=prices,
                    )
                )

        return plans

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch plans: {str(e)}",
        )


@router.post("/checkout", response_model=CreateCheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    user: User = Depends(require_verified_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> CreateCheckoutSessionResponse:
    """Create a Stripe checkout session for subscription."""
    try:
        # TODO: Get base URL from environment
        base_url = "http://localhost:3000"
        success_url = f"{base_url}/dashboard?subscription=success"
        cancel_url = f"{base_url}/dashboard/plans?subscription=canceled"

        checkout_url = subscription_service.create_checkout_session(
            user_id=user.id,
            user_email=user.email,
            price_id=request.price_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return CreateCheckoutSessionResponse(checkout_url=checkout_url)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}",
        )


@router.get("/current", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    user: User = Depends(require_verified_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> Optional[SubscriptionResponse]:
    """Get current user subscription."""
    subscription = subscription_service.get_user_subscription(user.id)

    if not subscription:
        return None

    return SubscriptionResponse(
        id=subscription.id,
        stripe_subscription_id=subscription.stripe_subscription_id,
        stripe_price_id=subscription.stripe_price_id,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        is_active=subscription.is_active(),
    )


@router.post("/cancel", status_code=status.HTTP_200_OK)
async def cancel_subscription(
    user: User = Depends(require_verified_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> dict:
    """Cancel current subscription at period end."""
    try:
        success = subscription_service.cancel_subscription(user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found",
            )

        return {"message": "Subscription will be canceled at the end of the billing period"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}",
        )
