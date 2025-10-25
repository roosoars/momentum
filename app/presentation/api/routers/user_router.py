"""API router for user authentication and management."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import (
    get_email_service,
    get_subscription_service,
    get_user_service,
)
from app.domain.models.user import User
from app.presentation.api.schemas.user_schemas import (
    UserLoginRequest,
    UserLoginResponse,
    UserProfileResponse,
    UserRegisterRequest,
    UserRegisterResponse,
    UserResendVerificationRequest,
    UserResponse,
    UserVerifyEmailRequest,
)
from app.services.email_service import EmailService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["users"])


def get_current_user(
    authorization: str = "",
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Dependency to get current authenticated user."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization[7:]
    payload = user_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = user_service.get_by_id(payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def require_verified_user(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency to require verified user."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
        )
    return user


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    user_service: UserService = Depends(get_user_service),
    email_service: EmailService = Depends(get_email_service),
) -> UserRegisterResponse:
    """Register a new user."""
    try:
        user, verification_token = user_service.register(
            email=request.email,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Send verification email
    # In production, use actual base URL from environment
    base_url = "http://localhost:3000"  # TODO: Get from env
    email_service.send_verification_email(
        to_email=user.email,
        verification_token=verification_token,
        base_url=base_url,
    )

    return UserRegisterResponse(
        user_id=user.id,
        email=user.email,
        message="Registration successful. Please check your email to verify your account.",
    )


@router.post("/login", response_model=UserLoginResponse)
async def login(
    request: UserLoginRequest,
    user_service: UserService = Depends(get_user_service),
) -> UserLoginResponse:
    """Login and get access token."""
    user = user_service.authenticate(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create JWT token
    access_token = user_service.create_token(user)

    return UserLoginResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
    )


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    request: UserVerifyEmailRequest,
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """Verify user email with token."""
    success = user_service.verify_email(request.token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    return {"message": "Email verified successfully"}


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    request: UserResendVerificationRequest,
    user_service: UserService = Depends(get_user_service),
    email_service: EmailService = Depends(get_email_service),
) -> dict:
    """Resend verification email."""
    user = user_service.get_by_email(request.email)

    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a verification email has been sent."}

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    try:
        verification_token = user_service.resend_verification(user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Send verification email
    base_url = "http://localhost:3000"  # TODO: Get from env
    email_service.send_verification_email(
        to_email=user.email,
        verification_token=verification_token,
        base_url=base_url,
    )

    return {"message": "Verification email sent"}


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    user: User = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> UserProfileResponse:
    """Get current user profile."""
    # Check if user has active subscription
    has_active_subscription = subscription_service.has_active_subscription(user.id)

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        is_verified=user.is_verified,
        has_active_subscription=has_active_subscription,
        created_at=user.created_at,
    )
