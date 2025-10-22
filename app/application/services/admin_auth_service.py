from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from ...domain.models import User
from ...domain.ports.persistence import PersistenceGateway

logger = logging.getLogger(__name__)


class AdminAuthService:
    """Manages administrator accounts and token-based authentication."""

    def __init__(
        self,
        persistence: PersistenceGateway,
        secret_key: str,
        token_exp_minutes: int = 1440,
        algorithm: str = "HS256",
    ) -> None:
        if not secret_key:
            raise RuntimeError("ADMIN_TOKEN_SECRET não configurado.")
        if secret_key == "change-me":
            logger.warning(
                "ADMIN_TOKEN_SECRET está usando o valor padrão. Configure um segredo seguro em produção."
            )
        self._persistence = persistence
        self._secret_key = secret_key
        self._token_exp_minutes = token_exp_minutes
        self._algorithm = algorithm
        self._pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # ------------------------------------------------------------------
    def ensure_default_admin(self, email: Optional[str], password: Optional[str]) -> Optional[User]:
        if not email or not password:
            return None
        existing = self._persistence.get_user_by_email(email.lower())
        if existing:
            return existing
        hashed = self._pwd.hash(password)
        logger.info("Creating default administrator account for %s", email)
        return self._persistence.create_user(email=email.lower(), password_hash=hashed)

    def register(self, email: str, password: str) -> User:
        email_clean = email.strip().lower()
        if not email_clean:
            raise ValueError("E-mail é obrigatório.")
        if not password or len(password) < 6:
            raise ValueError("Senha deve ter ao menos 6 caracteres.")
        if self._persistence.get_user_by_email(email_clean):
            raise ValueError("Já existe um administrador com este e-mail.")
        hashed = self._pwd.hash(password)
        return self._persistence.create_user(email=email_clean, password_hash=hashed)

    def authenticate(self, email: str, password: str) -> str:
        email_clean = email.strip().lower()
        user = self._persistence.get_user_by_email(email_clean)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")
        if not self._pwd.verify(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")
        return self._create_token(user)

    def verify_token(self, token: str) -> User:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.") from exc
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.") from exc
        user = self._persistence.get_user_by_id(user_id_int)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrador não encontrado.")
        return user

    def get_current_admin(self, token: str) -> User:
        user = self.verify_token(token)
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrador desativado.")
        return user

    def _create_token(self, user: User) -> str:
        now = datetime.now(tz=timezone.utc)
        expire = now + timedelta(minutes=self._token_exp_minutes)
        payload = {"sub": str(user.id), "email": user.email, "exp": expire}
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
