"""Service for user authentication and management."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt

from app.domain.models.user import User
from app.infrastructure.repositories.user_repository import UserRepository


class UserService:
    """Service for managing user authentication and registration."""

    def __init__(
        self,
        user_repository: UserRepository,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        jwt_expiration_hours: int = 24,
        verification_expiration_hours: int = 24,
    ):
        self.user_repository = user_repository
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expiration_hours = jwt_expiration_hours
        self.verification_expiration_hours = verification_expiration_hours

    def register(self, email: str, password: str) -> tuple[User, str]:
        """
        Register a new user.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Tuple of (User, verification_token)

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing_user = self.user_repository.get_by_email(email)
        if existing_user:
            raise ValueError("Email already registered")

        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        verification_expires_at = datetime.utcnow() + timedelta(
            hours=self.verification_expiration_hours
        )

        # Create user
        user = self.user_repository.create(
            email=email,
            password_hash=password_hash,
            verification_token=verification_token,
            verification_expires_at=verification_expires_at,
        )

        return user, verification_token

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User if authenticated, None otherwise
        """
        user = self.user_repository.get_by_email(email)
        if not user:
            return None

        # Verify password
        if not bcrypt.checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        ):
            return None

        return user

    def verify_email(self, token: str) -> bool:
        """
        Verify a user's email with verification token.

        Args:
            token: Verification token

        Returns:
            True if verified, False otherwise
        """
        user = self.user_repository.get_by_verification_token(token)
        if not user:
            return False

        # Check if token expired
        if user.verification_expires_at and user.verification_expires_at < datetime.utcnow():
            return False

        # Verify email
        self.user_repository.verify_email(user.id)
        return True

    def resend_verification(self, user_id: int) -> str:
        """
        Resend verification email.

        Args:
            user_id: User ID

        Returns:
            New verification token

        Raises:
            ValueError: If user not found or already verified
        """
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        if user.is_verified:
            raise ValueError("Email already verified")

        # Generate new token
        verification_token = secrets.token_urlsafe(32)
        verification_expires_at = datetime.utcnow() + timedelta(
            hours=self.verification_expiration_hours
        )

        self.user_repository.update_verification_token(
            user_id, verification_token, verification_expires_at
        )

        return verification_token

    def create_token(self, user: User) -> str:
        """
        Create JWT token for user.

        Args:
            user: User entity

        Returns:
            JWT token string
        """
        payload = {
            "user_id": user.id,
            "email": user.email,
            "is_verified": user.is_verified,
            "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.user_repository.get_by_id(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.user_repository.get_by_email(email)
